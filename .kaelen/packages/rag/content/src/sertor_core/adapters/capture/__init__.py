"""Host-specific transcript capture adapters (feature 031).

Each adapter implements the `TranscriptCaptureAdapter` port for one assistant/source. The
host-specific knowledge (path encoding, JSONL field names, block types) lives ONLY here
(Principio X); the service and the domain stay agnostic.
"""
