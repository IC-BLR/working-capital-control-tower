# Product demo video

Working Capital Intelligence demo aligned to the product model (Receivables + Payables).

## Output

- `Working_Capital_Control_Tower_Demo.mp4` — ~90s, 1920×1080
- Full screens (no crops), title/end cards, captions, Jenny Neural VO

## Storyline (product model)

1. Positioning — Working Capital Intelligence (not AR-only)  
2. Cash Calendar — Net Working Capital Exposure (receivables − payables)  
3. Receivables portfolio — outstanding due, overdue, aging  
4. Customer ranking — highest receivable due first  
5. Invoice level — due amount, date, overdue days  
6. Payables portfolio — vendor obligations & exposure  
7. Payable invoice — payment-ready vs blocked  
8. CFO AI Assistant — portfolio / partner / invoice Q&A  
9. Close — cash in, cash out, timing, risk, decisions  

## Regenerate

```bash
demo/.venv/bin/python demo/capture_frames.py
demo/.venv/bin/python demo/build_video.py
```
