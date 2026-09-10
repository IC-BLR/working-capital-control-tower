import { useEffect, useState } from "react";
import axios from "axios";
import {
  Upload,
  FileText,
  CheckCircle,
  XCircle,
  Loader2,
  RefreshCw,
  AlertCircle,
} from "lucide-react";
import { Button } from "../components/ui/button";
import { toast } from "sonner";

import { AR_API_BASE } from "../config";

export default function DataPipeline() {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [appendMode, setAppendMode] = useState(true);
  const [llmProvider, setLlmProvider] = useState("ollama");
  const [loadingLlm, setLoadingLlm] = useState(false);
  const [geminiKey, setGeminiKey] = useState("");
  const [savingGeminiKey, setSavingGeminiKey] = useState(false);

  /* =========================
     File Selection
     ========================= */

  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files);
    const csvFiles = selectedFiles.filter((f) => f.name.endsWith(".csv"));
    
    if (csvFiles.length !== selectedFiles.length) {
      toast.warning("Only CSV files are supported");
    }
    
    setFiles(csvFiles);
    setResult(null);
  };

  const removeFile = (index) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  /* =========================
     LLM Provider Settings
     ========================= */

  useEffect(() => {
    // Load current settings so we can show the active LLM provider
    const fetchSettings = async () => {
      try {
        setLoadingLlm(true);
        const res = await axios.get(`${AR_API_BASE}/settings`);
        const current = res.data?.llm_provider || "ollama";
        setLlmProvider(current);
        // We never read back the actual API key for security reasons,
        // but we can show that Gemini is configured if needed later.
      } catch (error) {
        console.error("Failed to load settings:", error);
        toast.error("Unable to load LLM settings. Using default (Ollama).");
      } finally {
        setLoadingLlm(false);
      }
    };

    fetchSettings();
  }, []);

  const handleLlmChange = async (provider) => {
    if (provider === llmProvider) return;

    try {
      setLoadingLlm(true);
      setLlmProvider(provider); // optimistic update
      await axios.put(`${AR_API_BASE}/settings/llm_provider`, null, {
        params: { provider },
      });
      toast.success(`LLM provider set to ${provider === "gemini" ? "Gemini" : "Ollama"}`);
    } catch (error) {
      console.error("Failed to update LLM provider:", error);
      toast.error(
        error.response?.data?.detail?.message ||
          "Failed to update LLM provider. Please try again."
      );
    } finally {
      setLoadingLlm(false);
    }
  };

  const handleSaveGeminiKey = async () => {
    if (!geminiKey.trim()) {
      toast.error("Please enter a Gemini API key");
      return;
    }

    try {
      setSavingGeminiKey(true);
      await axios.put(`${AR_API_BASE}/settings/gemini_api_key`, null, {
        params: { api_key: geminiKey.trim() },
      });
      toast.success("Gemini API key saved successfully");
      setGeminiKey("");
    } catch (error) {
      console.error("Failed to save Gemini API key:", error);
      toast.error(
        error.response?.data?.detail?.message ||
          "Failed to save Gemini API key. Please try again."
      );
    } finally {
      setSavingGeminiKey(false);
    }
  };

  /* =========================
     Upload & Process
     ========================= */

  const handleUpload = async () => {
    if (files.length === 0) {
      toast.error("Please select at least one CSV file");
      return;
    }

    setUploading(true);
    setResult(null);

    try {
      const formData = new FormData();
      files.forEach((file) => {
        formData.append("files", file);
      });

      const response = await axios.post(
        `${AR_API_BASE}/pipeline/upload?append=${appendMode}`,
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        }
      );

      setResult(response.data);
      toast.success(
        `Successfully processed ${response.data.summary.success_count} file(s)`
      );
    } catch (error) {
      console.error("Upload error:", error);
      const errorMsg =
        error.response?.data?.detail || "Failed to upload files";
      toast.error(errorMsg);
      setResult({
        success: false,
        error: errorMsg,
      });
    } finally {
      setUploading(false);
    }
  };

  /* =========================
     Render
     ========================= */

  return (
    <div className="space-y-8" data-testid="data-pipeline-page">
      {/* Header */}
      <div>
        <h1 className="page-title">Data Pipeline</h1>
        <p className="text-slate-500 mt-1">
          Upload CSV files to ingest payment allocation data and refresh views
        </p>
      </div>

      {/* Upload Section */}
      <div className="glass-card p-6 space-y-6">
        {/* Mode Selection */}
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              checked={appendMode}
              onChange={() => setAppendMode(true)}
              className="w-4 h-4"
            />
            <span className="text-sm font-medium">Append Mode</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              checked={!appendMode}
              onChange={() => setAppendMode(false)}
              className="w-4 h-4"
            />
            <span className="text-sm font-medium">Replace Mode</span>
          </label>
          <span className="text-xs text-slate-500">
            {appendMode
              ? "(Adds new records to existing data)"
              : "(Replaces all existing data)"}
          </span>
        </div>

        {/* File Input */}
        <div>
          <label className="block mb-2 text-sm font-medium text-slate-700">
            Select CSV Files
          </label>
          <div className="border-2 border-dashed border-slate-300 rounded-lg p-6 text-center hover:border-emerald-500 transition-colors">
            <input
              type="file"
              multiple
              accept=".csv"
              onChange={handleFileChange}
              className="hidden"
              id="file-input"
            />
            <label
              htmlFor="file-input"
              className="cursor-pointer flex flex-col items-center gap-2"
            >
              <Upload className="w-8 h-8 text-slate-400" />
              <span className="text-sm text-slate-600">
                Click to select CSV files or drag and drop
              </span>
              <span className="text-xs text-slate-500">
                Multiple files supported
              </span>
            </label>
          </div>
        </div>

        {/* File List */}
        {files.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm font-medium text-slate-700">
              Selected Files ({files.length})
            </p>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {files.map((file, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 bg-slate-50 rounded-lg"
                >
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-slate-500" />
                    <span className="text-sm text-slate-700">{file.name}</span>
                    <span className="text-xs text-slate-500">
                      ({(file.size / 1024).toFixed(2)} KB)
                    </span>
                  </div>
                  <button
                    onClick={() => removeFile(index)}
                    className="text-red-500 hover:text-red-700"
                  >
                    <XCircle className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Upload Button */}
        <Button
          onClick={handleUpload}
          disabled={files.length === 0 || uploading}
          className="w-full btn-primary"
        >
          {uploading ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Processing...
            </>
          ) : (
            <>
              <Upload className="w-4 h-4 mr-2" />
              Upload & Process Files
            </>
          )}
        </Button>
      </div>

      {/* Results Section */}
      {result && (
        <div className="space-y-4">
          {/* Summary */}
          {result.success && (
            <div className="glass-card p-6 border-l-4 border-emerald-500">
              <div className="flex items-start gap-3">
                <CheckCircle className="w-5 h-5 text-emerald-600 mt-0.5" />
                <div className="flex-1">
                  <h3 className="font-semibold text-emerald-900 mb-2">
                    Processing Complete
                  </h3>
                  <p className="text-sm text-slate-700 mb-4">
                    {result.message}
                  </p>

                  {/* Summary Stats */}
                  <div className="grid grid-cols-3 gap-4 mb-4">
                    <div className="bg-emerald-50 p-3 rounded-lg">
                      <p className="text-xs text-slate-600">Files Processed</p>
                      <p className="text-2xl font-bold text-emerald-700">
                        {result.summary.success_count}
                      </p>
                    </div>
                    <div className="bg-blue-50 p-3 rounded-lg border-2 border-blue-200">
                      <p className="text-xs text-slate-600 font-medium">New Records Added</p>
                      <p className="text-3xl font-bold text-blue-700">
                        {result.summary.total_rows_inserted.toLocaleString()}
                      </p>
                      <p className="text-xs text-blue-600 mt-1">
                        {result.summary.total_rows_inserted === 1 ? 'record' : 'records'} inserted to database
                      </p>
                    </div>
                    <div className="bg-purple-50 p-3 rounded-lg">
                      <p className="text-xs text-slate-600">Views Refreshed</p>
                      <p className="text-2xl font-bold text-purple-700">
                        {result.view_refresh?.refreshed_views || 0}
                      </p>
                    </div>
                  </div>

                  {/* View Refresh Status */}
                  {result.view_refresh && (
                    <div className="bg-slate-50 p-4 rounded-lg">
                      <div className="flex items-center gap-2 mb-2">
                        <RefreshCw className="w-4 h-4 text-emerald-600" />
                        <span className="text-sm font-medium text-slate-700">
                          Views Refreshed Successfully
                        </span>
                      </div>
                      <p className="text-xs text-slate-600">
                        All dependent views have been updated with the latest
                        data. Refresh timestamp:{" "}
                        {new Date(
                          result.view_refresh.timestamp
                        ).toLocaleString()}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Error State */}
          {!result.success && (
            <div className="glass-card p-6 border-l-4 border-red-500">
              <div className="flex items-start gap-3">
                <XCircle className="w-5 h-5 text-red-600 mt-0.5" />
                <div className="flex-1">
                  <h3 className="font-semibold text-red-900 mb-2">
                    Processing Failed
                  </h3>
                  <p className="text-sm text-red-700">{result.error}</p>
                </div>
              </div>
            </div>
          )}

          {/* File Details */}
          {result.files_processed && result.files_processed.length > 0 && (
            <div className="glass-card p-6">
              <h3 className="font-semibold text-slate-900 mb-4">
                File Processing Details
              </h3>
              <div className="space-y-2">
                {result.files_processed.map((fileResult, index) => (
                  <div
                    key={index}
                    className={`p-3 rounded-lg ${
                      fileResult.success
                        ? "bg-emerald-50"
                        : "bg-red-50"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {fileResult.success ? (
                          <CheckCircle className="w-4 h-4 text-emerald-600" />
                        ) : (
                          <XCircle className="w-4 h-4 text-red-600" />
                        )}
                        <span className="text-sm font-medium text-slate-700">
                          {fileResult.file.split("/").pop()}
                        </span>
                      </div>
                      {fileResult.success && (
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold text-emerald-700">
                            {fileResult.rows_inserted.toLocaleString()}
                          </span>
                          <span className="text-xs text-slate-600">
                            {fileResult.rows_inserted === 1 ? 'new record' : 'new records'} added
                          </span>
                        </div>
                      )}
                      {!fileResult.success && (
                        <span className="text-xs text-red-600">
                          {fileResult.error}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* LLM Settings */}
      <div className="glass-card p-4 flex flex-col gap-3 max-w-md">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold text-slate-800">
              LLM Provider
            </p>
            <p className="text-xs text-slate-500">
              Controls which LLM is used for AI insights (default is Ollama).
            </p>
          </div>
          {loadingLlm && (
            <span className="text-xs text-slate-400">Updating…</span>
          )}
        </div>
        <div className="flex items-center gap-4 mt-1">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="llm-provider"
              value="ollama"
              checked={llmProvider === "ollama"}
              onChange={() => handleLlmChange("ollama")}
              className="w-4 h-4"
            />
            <span className="text-sm font-medium">Ollama (Default)</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="llm-provider"
              value="gemini"
              checked={llmProvider === "gemini"}
              onChange={() => handleLlmChange("gemini")}
              className="w-4 h-4"
            />
            <span className="text-sm font-medium">Gemini</span>
          </label>
        </div>

        {llmProvider === "gemini" && (
          <div className="mt-3 space-y-2">
            <p className="text-xs text-slate-500">
              Enter your Gemini API key. It will be stored securely on the server in the
              backend <code>.env</code> file so your own model can be used.
            </p>
            <input
              type="password"
              className="border border-slate-300 rounded-md px-3 py-2 text-sm w-full"
              placeholder="GEMINI_API_KEY"
              value={geminiKey}
              onChange={(e) => setGeminiKey(e.target.value)}
            />
            <Button
              type="button"
              size="sm"
              className="btn-primary"
              onClick={handleSaveGeminiKey}
              disabled={savingGeminiKey}
            >
              {savingGeminiKey ? "Saving..." : "Save Gemini API Key"}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

