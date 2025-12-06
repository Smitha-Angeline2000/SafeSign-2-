# 💸💸 SafeSign 
### SafeSign is a web-based application designed to help professionals, students, and legal teams analyze PDF documents with precision. It combines **text extraction**, **clause detection**, and **GPT-powered summarization** to provide insights into legal, academic, and technical documents. The application provides a drag-and-drop interface for easy PDF uploads and delivers a detailed analysis report highlighting potential risks and key points from the document.
___
### Problem Statement:
Most users sign financial documents (loan agreements, insurance policies, EMI contracts, credit cards, mutual funds) without fully understanding hidden clauses, because:
- They are written in legal/financial jargon, not plain language.
- Risky clauses like lock-ins, penalty fees, auto-renewals, data-sharing, rejection conditions, and foreclosure charges are buried deep in the document.
- There is no tool that explains these documents simply before signing.
___
## What happens then?
- The common man eventually signs affidavits and legal documentation without knowing the traps and loss of money they lead to.
---

## Features

### Document Upload
- **Drag-and-drop interface** for seamless PDF uploads.
- Supports multiple PDF formats and large documents.
- Shows upload progress and immediate feedback for the user.

### Text Extraction
- Uses PyPDF2 for accurate text extraction from PDFs.
- Preserves the structure and formatting of the original document.
- Converts scanned PDFs into readable text for analysis (future OCR support possible).

### Clause Detection & Risk Analysis
SafeSign identifies key clauses in legal and contractual documents, such as:
- **Termination Clause**
- **Confidentiality Clause**
- **Payment Terms**
- **Liability Clause**
- **Dispute Resolution**

Each detected clause is marked as **YES/NO**, and an **overall risk score** is computed to provide an at-a-glance evaluation of the document's risk exposure.

### GPT-Powered Summary
- Uses OpenAI GPT API to generate a **concise, human-readable summary**.
- Summarizes large documents in seconds, highlighting important sections.
- Provides actionable insights and a clearer understanding of complex texts.

### Results Dashboard
- Displays **overall risk score** as a percentage.
- Lists **detected clauses** with YES/NO indicators.
- Shows the **full extracted text** from the PDF.
- Provides the **GPT-generated summary** for quick comprehension.
  



