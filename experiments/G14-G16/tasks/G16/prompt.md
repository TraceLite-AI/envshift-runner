In the Billing API queue, deduplicate reports for customer AC-72, invoice INV-1048, failure code PAY-RETRY-02. Among reports matching all three fields, keep the earliest-created report open as the canonical report. Resolve every other matching report as Duplicate and link each to that canonical report. Leave all other reports, titles, assignees, and comments unchanged. You can compare selected reports to inspect their full details together.

Use the visible application and browser UI only. Do not open a terminal or DevTools, execute code, or browse other websites.
