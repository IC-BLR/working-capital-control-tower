"""LLM service for AI insights."""
import json
import re
import logging
from typing import Dict, Any, Optional

from ar.services.llm.factory import LLMProviderFactory
from ar.services.llm.providers.base import (
    BaseLLMProvider,
    LLMProviderError,
    LLMProviderTimeoutError,
    LLMProviderConnectionError,
    LLMProviderAuthenticationError,
    LLMProviderRateLimitError
)

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Base exception for LLM errors."""
    pass


class LLMTimeoutError(LLMError):
    """Raised when LLM request times out."""
    def __init__(self, timeout: int, model: str):
        logger.info(f"LLM request has timed out for model :{model}")
        self.timeout = timeout
        self.model = model
        super().__init__(f"LLM request timed out after {timeout}s for model {model}")


class LLMConnectionError(LLMError):
    """Raised when LLM connection fails."""
    def __init__(self, model: str, message: str):
        logger.error(f"LLM connection error occurred for model: {model} with message: {message}")
        self.model = model
        super().__init__(f"LLM connection error for model {model}: {message}")


class LLMProcessingError(LLMError):
    """Raised when LLM response processing fails."""
    pass


class LLMService:
    """Service for LLM-based analysis with configurable provider support."""
    
    def __init__(
        self,
        provider_name: Optional[str] = None,
        model: Optional[str] = None,
        **provider_kwargs
    ):
        """
        Initialize LLM service with configurable provider.
        
        Args:
            provider_name: Provider name (defaults to LLM_PROVIDER env var or "ollama")
            model: Model name (defaults to LLM_MODEL env var or provider default)
            **provider_kwargs: Additional provider-specific configuration
        """
        logger.info(f"Initializing LLMService. Requested Provider: {provider_name}")
        try:
            self.provider: BaseLLMProvider = LLMProviderFactory.create_provider(
                provider_name=provider_name,
                model=model,
                **provider_kwargs
            )
            self.model = self.provider.get_model()
            logger.info(
                f"LLMService initialized with provider: {self.provider.get_provider_name()}, "
                f"model: {self.model}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize LLM provider: {str(e)}")
            raise ValueError(f"Failed to initialize LLM provider: {str(e)}")
    
    def _extract_json(self, output: str) -> Dict[str, Any]:
        logger.info("Extracting JSON from LLM output")
        """Extract JSON from LLM output, handling common formatting issues."""
        if not output:
            raise LLMProcessingError("Empty response from LLM")
        
        # Log raw output for debugging
        logger.info(f"Raw output length: {len(output)}, first 300 chars: {repr(output[:300])}")
        
        # Find JSON boundaries - use brace matching for more reliable extraction
        json_start = output.find("{")
        
        if json_start < 0:
            # Try to find JSON in a different way - maybe it's wrapped in markdown code blocks
            if "```json" in output:
                json_start = output.find("```json") + 7
                json_end_marker = output.find("```", json_start)
                if json_end_marker > json_start:
                    output = output[json_start:json_end_marker].strip()
                    json_start = output.find("{")
            
            if json_start < 0:
                logger.error(f"No opening brace found. Output preview: {output[:500]}")
                raise LLMProcessingError("No opening brace found in LLM response")
        
        # Use brace matching to find the correct closing brace
        brace_count = 0
        json_end = json_start
        in_string = False
        escape_next = False
        
        for i, char in enumerate(output[json_start:], start=json_start):
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_end = i + 1
                        break
        
        if brace_count != 0:
            logger.warning(f"Unmatched braces (count: {brace_count}), using end of string or last closing brace")
            # Try to use the last closing brace as fallback
            last_brace = output.rfind("}", json_start)
            if last_brace > json_start:
                json_end = last_brace + 1
            else:
                json_end = len(output)
        
        json_str = output[json_start:json_end]
        logger.info(f"Extracted JSON string (length: {len(json_str)}, start: {json_start}, end: {json_end})")
        
        # Try to parse JSON
        try:
            parsed = json.loads(json_str)
            logger.info(f"Successfully parsed JSON with keys: {list(parsed.keys())}")
            return parsed
        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode error: {str(e)} at position {e.pos if hasattr(e, 'pos') else 'unknown'}")
            # Try to fix common JSON issues
            fixed_json = json_str
            
            # Remove trailing commas before } or ]
            fixed_json = re.sub(r',\s*}', '}', fixed_json)
            fixed_json = re.sub(r',\s*]', ']', fixed_json)
            
            # Remove comments (// and /* */)
            fixed_json = re.sub(r'//.*$', '', fixed_json, flags=re.MULTILINE)
            fixed_json = re.sub(r'/\*.*?\*/', '', fixed_json, flags=re.DOTALL)
            
            # Try to close incomplete JSON strings
            if fixed_json.count('"') % 2 != 0:
                # Unclosed string, try to close it at the end
                if not fixed_json.rstrip().endswith('"'):
                    fixed_json = fixed_json.rstrip() + '"'
            
            # Try to close incomplete JSON object/array
            open_braces = fixed_json.count('{')
            close_braces = fixed_json.count('}')
            if open_braces > close_braces:
                fixed_json += '}' * (open_braces - close_braces)
            
            open_brackets = fixed_json.count('[')
            close_brackets = fixed_json.count(']')
            if open_brackets > close_brackets:
                fixed_json += ']' * (open_brackets - close_brackets)
            
            try:
                parsed = json.loads(fixed_json)
                logger.info(f"Successfully parsed fixed JSON with keys: {list(parsed.keys())}")
                return parsed
            except json.JSONDecodeError as e2:
                logger.warning(f"Fixed JSON still failed: {str(e2)}. Attempting regex extraction...")
                # Last resort: try to extract key fields using regex
                result = {}
                
                # Extract common fields with more lenient patterns
                fields = [
                    ("risk_assessment", r'"risk_assessment"\s*:\s*"([^"]+)"'),
                    ("trend", r'"trend"\s*:\s*"([^"]+)"'),
                    ("explanation", r'"explanation"\s*:\s*"([^"]*(?:\\.[^"]*)*?)"(?:\s*[,}])'),
                    ("recommendations", r'"recommendations"\s*:\s*\[(.*?)\]'),
                    ("key_findings", r'"key_findings"\s*:\s*\[(.*?)\]'),
                    ("payment_behavior_summary", r'"payment_behavior_summary"\s*:\s*"([^"]*(?:\\.[^"]*)*?)"(?:\s*[,}])'),
                ]
                
                for field_name, pattern in fields:
                    match = re.search(pattern, json_str, re.DOTALL)
                    if match:
                        if field_name in ["recommendations", "key_findings"]:
                            # Try to parse as JSON array
                            try:
                                result[field_name] = json.loads(f"[{match.group(1)}]")
                            except:
                                # Try to extract array items manually
                                items = re.findall(r'"([^"]+)"', match.group(1))
                                result[field_name] = items if items else []
                        else:
                            # Unescape the string
                            value = match.group(1).replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t')
                            result[field_name] = value
                
                # If we extracted at least explanation, consider it a partial success
                if "explanation" in result and result.get("explanation"):
                    logger.warning(f"Partial JSON extraction succeeded. Extracted keys: {list(result.keys())}")
                    return result
                
                # Log the problematic JSON for debugging
                logger.error(f"Failed to parse JSON. First 500 chars: {json_str[:500]}")
                logger.error(f"Last 200 chars: {json_str[-200:] if len(json_str) > 200 else json_str}")
                raise LLMProcessingError(f"Failed to parse JSON from LLM response: {str(e)}. JSON length: {len(json_str)}")
    
    def _call_llm(self, prompt: str, **kwargs) -> str:
        logger.info("Calling LLM provider with prompt")
        """
        Call LLM provider with the given prompt.
        
        Args:
            prompt: Input prompt
            **kwargs: Provider-specific parameters
            
        Returns:
            Generated text response
        """
        try:
            logger.info(
                f"Calling {self.provider.get_provider_name()} provider "
                f"with model: {self.model}"
            )
            output = self.provider.generate(prompt, **kwargs)
            logger.info(f"Provider returned output (length: {len(output) if output else 0})")
            return output
            
        except LLMProviderTimeoutError as e:
            raise LLMTimeoutError(e.timeout, e.model)
        except LLMProviderConnectionError as e:
            raise LLMConnectionError(e.model, str(e))
        except LLMProviderAuthenticationError as e:
            raise LLMConnectionError(self.model, f"Authentication failed: {str(e)}")
        except LLMProviderRateLimitError as e:
            raise LLMConnectionError(self.model, f"Rate limit exceeded: {str(e)}")
        except LLMProviderError as e:
            raise LLMConnectionError(self.model, str(e))
        except Exception as e:
            logger.error(f"Unexpected error calling LLM provider: {str(e)}")
            raise LLMConnectionError(self.model, str(e))
    
    def analyze_partner_risk(self, partner_data: Dict[str, Any], recent_invoices: list) -> Dict[str, Any]:
        logger.info("Analyzing partner risk using LLM")
        """
        Analyze partner risk based on partner details and recent invoices.
        
        Args:
            partner_data: Dictionary containing partner risk metrics and scores
            recent_invoices: List of recent invoice dictionaries
            
        Returns:
            Dictionary with AI risk assessment and insights
        """
        prompt = f"""
You are a senior credit risk analyst specializing in partner payment behavior analysis.

Analyze the following partner's risk profile and provide comprehensive insights:

PARTNER RISK METRICS:
- Risk Bucket: {partner_data.get('risk_bucket', 'UNKNOWN')}
- Net Risk Score: {partner_data.get('net_risk_score', 0):.2f}
- Percentile Position: {partner_data.get('percentile_ranking', {}).get('position', 'Unknown')}

SCORE BREAKDOWN:
- Cashflow Continuity: {partner_data.get('score_breakdown', {}).get('cashflow_continuity', {}).get('score', 0):.2f}/50
- Cashflow Strength: {partner_data.get('score_breakdown', {}).get('cashflow_strength', {}).get('score', 0):.2f}/40
- Low Overdue Bonus: {partner_data.get('score_breakdown', {}).get('low_overdue', {}).get('score', 0):.2f}/20
- Severe Stress Penalty: -{partner_data.get('score_breakdown', {}).get('penalty_severe_stress', {}).get('penalty', 0):.2f}
- Old Overdue Penalty: -{partner_data.get('score_breakdown', {}).get('penalty_old_overdue', {}).get('penalty', 0):.2f}

KEY METRICS:
- Total Runs: {partner_data.get('metrics', {}).get('total_runs', 0)}
- Paid Runs: {partner_data.get('metrics', {}).get('paid_runs', 0)}
- Fully Paid Runs: {partner_data.get('metrics', {}).get('fully_paid_runs', 0)}
- Stressed Runs: {partner_data.get('metrics', {}).get('stressed_runs', 0)}
- Severely Stressed Runs: {partner_data.get('metrics', {}).get('severely_stressed_runs', 0)}
- Avg Invoice Amount: ₹{partner_data.get('metrics', {}).get('avg_invoice_amount', 0):,.0f}
- Avg Allocated Amount: ₹{partner_data.get('metrics', {}).get('avg_allocated_amount', 0):,.0f}
- Avg Due Amount: ₹{partner_data.get('metrics', {}).get('avg_due_amount', 0):,.0f}
- Old Overdue Amount: ₹{partner_data.get('metrics', {}).get('old_overdue_amount', 0):,.0f}

CURRENT EXPOSURE (USE THESE EXACT VALUES - DO NOT CALCULATE OR ESTIMATE):
- Total Outstanding Amount (Due Amount): ₹{partner_data.get('metrics', {}).get('total_due_amount', 0):,.0f}
- Total Allocated Amount: ₹{partner_data.get('metrics', {}).get('total_allocated_amount', 0):,.0f}
- Unallocated Amount: ₹{partner_data.get('metrics', {}).get('unallocated_amount', 0):,.0f}

CRITICAL: When mentioning amounts in findings/recommendations, you MUST use the EXACT values from "CURRENT EXPOSURE" above. Convert to Crores (divide by 10,000,000) and format as **₹X.XX Cr**. Example: If Total Outstanding Amount is ₹155,000,000, write **₹15.50 Cr** (NOT ₹15 Cr or ₹16 Cr).

RECENT INVOICES (Last {len(recent_invoices)} invoices):
{json.dumps(recent_invoices[:50], indent=2, default=str)}

MARKET/NEWS/MEDIA CONTEXT:
Partner: {partner_data.get('partner_name', 'Unknown')} (Code: {partner_data.get('partner_code', 'Unknown')})

For this partner, you MUST provide relevant market/industry context. Use your knowledge of:
- The company's industry sector and recent sector trends
- General market conditions affecting this industry
- Industry-specific challenges or opportunities
- Sector performance indicators
- Regulatory or policy changes affecting the sector

EXAMPLES:
- For defense/electronics companies (e.g., Bharat Electronics): Reference defense sector growth, government contracts, Make in India initiatives, defense modernization, electronics manufacturing trends
- For retail/e-commerce: Reference consumer spending trends, digital transformation, competition, market expansion
- For IT/technology: Reference digital transformation, cloud adoption, IT spending trends, talent market
- For manufacturing: Reference industrial production, supply chain trends, export-import dynamics

REQUIREMENTS:
- ALWAYS provide sector/industry context for Finding 4 - do NOT default to "no news found" unless the company is completely unknown
- Include 5-10 relevant keywords from the sector/industry (e.g., defense, electronics, government contracts, manufacturing, Make in India)
- Focus on how sector trends might impact payment behavior and credit risk
- Use general industry knowledge - this is acceptable and expected
- DO NOT make up specific news articles with dates, but DO reference general sector trends and industry conditions

Analyze:
1. Overall risk assessment based on the risk bucket and score
2. Payment behavior trends from recent invoices
3. Key risk factors and concerns
4. Strengths and positive indicators
5. Recommendations for risk management

Respond ONLY with valid JSON matching this EXACT structure:

{{
  "risk_assessment": "Low Risk" | "Medium Risk" | "High Risk",
  "trend": "improving" | "stable" | "deteriorating",
  "explanation": "Provide a comprehensive 4-6 sentence analysis covering: (1) overall risk assessment and why; (2) payment behavior patterns observed in recent invoices; (3) key risk factors or strengths; (4) how this compares to typical partner behavior; (5) what the trend indicates for future risk; and (6) specific concerns or positive indicators.",
  "key_findings": [
    "Finding 1: specific observation from the data. MUST use exact amounts from CURRENT EXPOSURE section above. Format as **₹X.XX Cr** (e.g., if Total Outstanding Amount is ₹155,000,000, write **₹15.50 Cr**). Provide actionable insight based on this amount.",
    "Finding 2: MUST use the exact Unallocated Amount from CURRENT EXPOSURE section. Format as **₹X.XX Cr**. If unallocated amount is ₹0, state \"Unallocated amount is **₹0.00 Cr**\" and explain what this means (e.g., all payments properly allocated, no reconciliation needed). If unallocated amount > 0, explain the risk and suggest action.",
    "Finding 3: additional insight with exact amounts from CURRENT EXPOSURE formatted as **₹X.XX Cr**. Connect the amount to payment behavior patterns or risk implications.",
    "Finding 4: **Latest market findings:** MUST provide sector/industry context for this partner. Reference relevant industry trends, sector performance, market conditions, or regulatory changes affecting the partner's industry. Include 5–10 relevant keywords for UI highlighting (e.g., defense, electronics, government contracts, manufacturing, retail, e-commerce, technology, market expansion, competition, Make in India). Explain how these sector trends might impact payment behavior. Connect market findings with actual payment data - if outstanding amount is high, relate it to sector challenges; if low, relate to sector stability. Only if the company is completely unknown or unidentifiable, write: \"No recent credible market/news mentions were found or provided.\""
  ],
  "recommendations": [
    "Recommendation 1: specific actionable advice. If mentioning unallocated amount, use EXACT value from CURRENT EXPOSURE (format as **₹X.XX Cr**).",
    "Recommendation 2: another actionable recommendation with exact amounts from CURRENT EXPOSURE if applicable.",
    "Recommendation 3: additional recommendation",
    "Recommendation 4: **Action based on latest Market Analysis:** Provide 1–2 actionable recommendations based on industry trends or market context mentioned in Finding 4. Connect recommendations to actual payment data (outstanding amounts, unallocated amounts) and sector trends. If Finding 4 stated no news found, write exactly: \"No news-based recommendation (no recent credible mentions found or provided).\""
  ],
  "payment_behavior_summary": "2-3 sentence summary of payment patterns from recent invoices"
}}

Rules:
- Base your assessment on the actual risk metrics and invoice data provided
- CRITICAL FORMAT REQUIREMENT: You MUST return exactly 4 items in key_findings array labeled as "Finding 1:", "Finding 2:", "Finding 3:", "Finding 4:". You MUST return exactly 4 items in recommendations array labeled as "Recommendation 1:", "Recommendation 2:", "Recommendation 3:", "Recommendation 4:". Do NOT skip numbers or use different labels.
- CRITICAL AMOUNT ACCURACY: When mentioning amounts, you MUST use the EXACT values from the "CURRENT EXPOSURE" section above. Convert to Crores by dividing by 10,000,000 and format as **₹X.XX Cr** with 2 decimal places. Example: ₹155,000,000 = **₹15.50 Cr**. DO NOT round, estimate, or calculate amounts differently.
- ALWAYS include outstanding/due amount (Total Outstanding Amount from CURRENT EXPOSURE) in at least one key finding when discussing payment issues
- ALWAYS mention unallocated amount in recommendations if unallocated_amount > 0, suggesting it should be settled early. Use the EXACT unallocated amount from CURRENT EXPOSURE.
- When mentioning amounts in key_findings or recommendations, wrap them in double asterisks (**₹X.XX Cr**) for UI highlighting
- For market findings (Finding 4): You MUST provide sector/industry context. Reference the partner's industry sector, recent sector trends, market conditions, regulatory changes, or industry-specific developments that could impact payment behavior. Include 5–10 relevant keywords from the sector. CRITICAL: Connect market findings with actual payment data from CURRENT EXPOSURE - if outstanding amount is high, explain how sector challenges might contribute; if low, explain how sector stability supports payment reliability. Use your general knowledge of industries and sectors - this is expected and acceptable. Only default to "No recent credible market/news mentions were found or provided" if the company is completely unknown or unidentifiable. For companies like Bharat Electronics (defense/electronics), Flipkart (e-commerce), Team Computers (IT/technology), or other well-known companies, ALWAYS provide relevant sector context.
- For Recommendation 4 (Action based on latest Market Analysis): Base it on the market context from Finding 4 AND connect it to actual payment data. If outstanding amount is high, suggest sector-specific mitigation strategies. If unallocated amount is significant, suggest industry-appropriate settlement approaches. If Finding 4 stated no news found, use the exact phrase: "No news-based recommendation (no recent credible mentions found or provided)."
- Recommendations should be actionable and relevant to the risk level
- The explanation should read like a professional credit risk analyst summary
- DO NOT include any text outside the JSON object
- DO NOT include markdown code blocks (```json) - return ONLY the raw JSON object
- If the input data has not changed, the output should remain consistent
- Start your response directly with {{ and end with }}

CRITICAL: Return ONLY valid JSON. No explanatory text before or after the JSON object.
"""
        
        try:
            provider_name = self.provider.get_provider_name()
            logger.info(
                f"Calling LLM with provider: {provider_name}, "
                f"model: {self.model} for partner risk analysis"
            )
            
            output = self._call_llm(prompt)
            logger.info(f"LLM ({provider_name}) returned output (length: {len(output) if output else 0})")
            
            if not output or len(output.strip()) == 0:
                logger.error(f"LLM ({provider_name}) returned empty response")
                raise LLMProcessingError("LLM returned empty response")
            
            # Extract JSON from response (works for all providers)
            result = self._extract_json(output)
            logger.info(f"Extracted JSON from {provider_name} response with keys: {list(result.keys())}")
            
            # Validate that we have essential fields - be lenient, only require explanation
            if "explanation" not in result or not result.get("explanation"):
                logger.warning(
                    f"LLM ({provider_name}) response missing explanation field. "
                    f"Available keys: {list(result.keys())}"
                )
                raise LLMProcessingError("LLM response missing explanation field")
            
            # Ensure required fields have defaults if missing (provider-agnostic)
            result.setdefault("risk_assessment", partner_data.get('risk_bucket', 'Unknown'))
            result.setdefault("trend", "stable")
            result.setdefault("key_findings", [])
            result.setdefault("recommendations", [])
            result.setdefault("payment_behavior_summary", "Analysis based on recent invoice patterns.")
            
            # Validate and fix format: Ensure exactly 4 findings and 4 recommendations with correct labels
            if isinstance(result.get("key_findings"), list):
                findings = result["key_findings"]
                # Ensure we have exactly 4 findings
                if len(findings) < 4:
                    # Pad with default findings if needed
                    for i in range(len(findings), 4):
                        findings.append(f"Finding {i+1}: Analysis based on payment data.")
                elif len(findings) > 4:
                    # Trim to 4 if more than 4
                    findings = findings[:4]
                # Ensure correct labels (remove any existing "Finding X:" and add correct one)
                for i, finding in enumerate(findings):
                    # Remove any existing "Finding X:" pattern
                    cleaned = re.sub(r'^Finding \d+:\s*', '', str(finding))
                    findings[i] = f"Finding {i+1}: {cleaned.strip()}"
                result["key_findings"] = findings
            
            if isinstance(result.get("recommendations"), list):
                recommendations = result["recommendations"]
                # Ensure we have exactly 4 recommendations
                if len(recommendations) < 4:
                    # Pad with default recommendations if needed
                    for i in range(len(recommendations), 4):
                        recommendations.append(f"Recommendation {i+1}: Monitor partner performance.")
                elif len(recommendations) > 4:
                    # Trim to 4 if more than 4
                    recommendations = recommendations[:4]
                # Ensure correct labels (remove any existing "Recommendation X:" and add correct one)
                for i, rec in enumerate(recommendations):
                    # Remove any existing "Recommendation X:" pattern
                    cleaned = re.sub(r'^Recommendation \d+:\s*', '', str(rec))
                    recommendations[i] = f"Recommendation {i+1}: {cleaned.strip()}"
                result["recommendations"] = recommendations
            
            # Mark as successful (no error field)
            result["is_fallback"] = False
            result.pop("error", None)
            
            logger.info(
                f"Successfully processed {provider_name} response. "
                f"is_fallback: {result.get('is_fallback')}, "
                f"has_explanation: {'explanation' in result}"
            )
            return result
        except (LLMTimeoutError, LLMConnectionError, LLMProcessingError) as e:
            # Log the specific error with provider context
            provider_name = self.provider.get_provider_name()
            logger.error(
                f"LLM ({provider_name}) error ({type(e).__name__}): {str(e)}. "
                f"Returning fallback response."
            )
            # Return fallback response on error (same format for all providers)
            return {
                "risk_assessment": partner_data.get('risk_bucket', 'Unknown'),
                "trend": "stable",
                "explanation": f"AI analysis temporarily unavailable. Risk assessment based on calculated metrics: {partner_data.get('risk_bucket', 'Unknown')} risk with score {partner_data.get('net_risk_score', 0):.2f}.",
                "key_findings": [
                    f"Risk bucket: {partner_data.get('risk_bucket', 'Unknown')}",
                    f"Net risk score: {partner_data.get('net_risk_score', 0):.2f}",
                    f"Payment runs: {partner_data.get('metrics', {}).get('paid_runs', 0)}/{partner_data.get('metrics', {}).get('total_runs', 0)}"
                ],
                "recommendations": [
                    "Monitor payment behavior closely",
                    "Review overdue amounts regularly",
                    "Maintain communication with partner"
                ],
                "payment_behavior_summary": "Analysis based on calculated risk metrics.",
                "is_fallback": True,
                "error": str(e)
            }
        except Exception as e:
            # Catch any other unexpected errors
            provider_name = self.provider.get_provider_name()
            logger.error(
                f"Unexpected error in LLM ({provider_name}) analysis: {str(e)}",
                exc_info=True
            )
            return {
                "risk_assessment": partner_data.get('risk_bucket', 'Unknown'),
                "trend": "stable",
                "explanation": f"AI analysis temporarily unavailable. Risk assessment based on calculated metrics: {partner_data.get('risk_bucket', 'Unknown')} risk with score {partner_data.get('net_risk_score', 0):.2f}.",
                "key_findings": [
                    f"Risk bucket: {partner_data.get('risk_bucket', 'Unknown')}",
                    f"Net risk score: {partner_data.get('net_risk_score', 0):.2f}",
                    f"Payment runs: {partner_data.get('metrics', {}).get('paid_runs', 0)}/{partner_data.get('metrics', {}).get('total_runs', 0)}"
                ],
                "recommendations": [
                    "Monitor payment behavior closely",
                    "Review overdue amounts regularly",
                    "Maintain communication with partner"
                ],
                "payment_behavior_summary": "Analysis based on calculated risk metrics.",
                "is_fallback": True,
                "error": str(e)
            }

