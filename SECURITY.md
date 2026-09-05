# Security and Data Handling

## Supported versions

This is an early reference implementation. Security fixes are applied to the latest version only.

## Reporting a vulnerability

Please use GitHub's private vulnerability-reporting feature when enabled. Do not open a public issue containing exploit details, credentials, customer information, or proprietary product data.

## Data boundary

The repository is designed for synthetic examples. Do not commit:

- Customer personally identifiable information
- Authentication material or API keys
- Private pricing or contracts
- Confidential workloads or datasets
- Proprietary support, return, or win/loss records
- Vendor-confidential roadmaps or compatibility information

A production deployment requires authentication, authorization, encryption, retention, deletion, audit, and tenant-isolation controls that are outside this reference implementation.
