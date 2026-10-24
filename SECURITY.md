# Security Policy

## Authorized use

`loadforge` is a **defensive tool for systems you own or are explicitly authorized to
test**. Do not point it at third-party infrastructure without written permission;
unauthorized security testing violates computer-misuse laws in most jurisdictions.

`loadforge` refuses non-loopback targets unless `--allow-public` is passed explicitly. It sends bounded GET requests only — no amplification, reflection, spoofing, or botnet features exist. Use it exclusively against infrastructure you own or are contracted to test, and respect your own rate limits.

## Reporting a vulnerability

If you find a vulnerability or unsafe default in `loadforge` itself, please open a
private security advisory on the GitHub repository (or open an issue describing the
problem at a high level if you cannot use advisories). We will acknowledge within
72 hours and coordinate a fix before public disclosure.

## Secrets

`loadforge` stores no credentials and requires none. Do not commit real tokens, cookies
or keys to the spec/example files in this repository; `.gitignore` excludes `.env`
and common key material.
