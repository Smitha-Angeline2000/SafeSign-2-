# 💸 SafeSign 💸 
SafeSign is a web-based application designed to help professionals, students, and legal teams analyze PDF documents with precision. It combines **text extraction**, **clause detection**, and **GPT-powered summarization** to provide insights into legal, academic, and technical documents. The application provides a drag-and-drop interface for easy PDF uploads and delivers a detailed analysis report highlighting potential risks and key points from the document.
___
### Problem Statement:
Most users sign financial documents (loan agreements, insurance policies, EMI contracts, credit cards, mutual funds) without fully understanding hidden clauses, because:
- They are written in legal/financial jargon, not plain language.
- Risky clauses like lock-ins, penalty fees, auto-renewals, data-sharing, rejection conditions, and foreclosure charges are buried deep in the document.
- There is no tool that explains these documents simply before signing.
___
## What happens then?
- Many people sign contracts or documents without fully understanding the legal consequences.

- This can result in financial loss, unwanted obligations, or legal disputes.

- SafeSign automatically analyzes PDF documents and extracts key clauses.

- It assesses potential risks associated with each clause, giving an overall risk score.

- Provides a plain-language summary of the document for quick understanding.

- Empowers users to make informed decisions before signing important documents.

- Acts as a digital safeguard against hidden legal and financial pitfalls.

- Makes legal information accessible and actionable, reducing the chances of unintended commitments.
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

<p align="center">
  <a href="https://ibb.co/fzm6Kt76"><img src="https://i.ibb.co/1tHypKxy/Whats-App-Image-2025-12-06-at-16-33-23.jpg" alt="Whats-App-Image-2025-12-06-at-16-33-23" border="0"> </a> 
</p>


### GPT-Powered Summary
- Uses OpenAI GPT API to generate a **concise, human-readable summary**.
- Summarizes large documents in seconds, highlighting important sections.
- Provides actionable insights and a clearer understanding of complex texts.

### Results Dashboard
- Displays **overall risk score** as a percentage.
- Lists **detected clauses** with YES/NO indicators.
- Shows the **full extracted text** from the PDF.
- Provides the **GPT-generated summary** for quick comprehension.
  



