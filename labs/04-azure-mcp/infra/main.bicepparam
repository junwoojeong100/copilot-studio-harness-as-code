using './main.bicep'

// Values come from environment variables set by scripts/deploy.sh, so the API key never appears
// on a command line or in a file that is committed.
param apiKey = readEnvironmentVariable('API_KEY')
param imageTag = readEnvironmentVariable('IMAGE_TAG', '')
param keyFingerprint = readEnvironmentVariable('KEY_FINGERPRINT', '')
param deleteAfter = readEnvironmentVariable('DELETE_AFTER', '2026-10-24')
