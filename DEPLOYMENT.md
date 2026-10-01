# Cloud Run Deployment

**Status: NOT DEPLOYED.** No cloud-changing command in this runbook has been executed. `gcloud` is not installed in the current workspace terminal, no GCP project/auth context is configured, and the live URL is pending. The commands below are staged for Cloud Shell or an authenticated Google Cloud SDK terminal. Obtain explicit confirmation before running each resource-changing command.

The runtime uses a Gemini API key (not Vertex AI auth), Firestore, Secret Manager-mounted environment variables, a Maps Places API key, and ADC-backed Speech/TTS clients. Translation is not called by the app; Cloud Run captures structured stdout logs. The Vertex AI User, Cloud Translation User, and Logs Writer grants below are included only because they were explicitly requested; they are not required by current code. Speech and Text-to-Speech roles are additionally needed for the app's existing voice calls. Confirm this role set before applying any IAM command.

## 1. Read-Only Preflight

Run in Bash / Cloud Shell after installing or opening the Google Cloud SDK. These commands inspect local configuration and do not create cloud resources.

```bash
export PROJECT_ID="$(gcloud config get-value project 2>/dev/null)"
test -n "$PROJECT_ID" && test "$PROJECT_ID" != "(unset)"
export REGION="asia-south1"
export SERVICE="sakhi-app"
export RUNTIME_SA_NAME="sakhi-runtime"
export RUNTIME_SA="${RUNTIME_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
export MAPS_SECRET="sakhi-maps-api-key"
export GEMINI_SECRET="sakhi-gemini-api-key"
gcloud auth list
gcloud projects describe "$PROJECT_ID"
```

For the Gemini secret, provide `GEMINI_KEY_FILE` as the path to a protected file outside this repository. Never paste key material into this file, chat, or shell command history.

## 2. Enable APIs

**Cloud-changing; confirm before running.** The API Keys API is added because a Places-restricted Maps key is created below; IAM and Service Usage APIs support service-account and API setup.

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  aiplatform.googleapis.com \
  speech.googleapis.com \
  texttospeech.googleapis.com \
  translate.googleapis.com \
  firestore.googleapis.com \
  secretmanager.googleapis.com \
  logging.googleapis.com \
  places.googleapis.com \
  apikeys.googleapis.com \
  iam.googleapis.com \
  serviceusage.googleapis.com \
  --project="$PROJECT_ID"
```

## 3. Runtime Identity and IAM

**Cloud-changing; confirm each grant before running.** This creates a dedicated service account, not the default Compute Engine account.

```bash
gcloud iam service-accounts create "$RUNTIME_SA_NAME" \
  --display-name="Sakhi Cloud Run runtime" \
  --project="$PROJECT_ID"
```

The requested project-level roles are shown individually so each can be approved separately:

```bash
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$RUNTIME_SA" \
  --role="roles/aiplatform.user"
```

```bash
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$RUNTIME_SA" \
  --role="roles/datastore.user"
```

```bash
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$RUNTIME_SA" \
  --role="roles/cloudtranslate.user"
```

```bash
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$RUNTIME_SA" \
  --role="roles/logging.logWriter"
```

The current Speech and TTS implementations use Application Default Credentials. These additional roles are needed for those API calls; they were not in the requested list:

```bash
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$RUNTIME_SA" \
  --role="roles/speech.client"
```

```bash
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$RUNTIME_SA" \
  --role="roles/texttospeech.user"
```

Secret Accessor will be granted on the two secrets individually in section 4 rather than project-wide.

## 4. Restricted Maps Key and Secrets

**Cloud-changing; confirm each command before running.** Create the API key with an API restriction to Places only. The key string is written to a mode-600 temporary file, not printed to the terminal, then uploaded as a Secret Manager version.

```bash
MAPS_KEY_RESOURCE="$(gcloud services api-keys create \
  --display-name="Sakhi Places API key" \
  --api-target="service=places.googleapis.com" \
  --project="$PROJECT_ID" \
  --format="value(name)")"
MAPS_KEY_FILE="$(mktemp)"
chmod 600 "$MAPS_KEY_FILE"
gcloud services api-keys get-key-string "$MAPS_KEY_RESOURCE" \
  --format="value(keyString)" > "$MAPS_KEY_FILE"
```

Create the two secret resources:

```bash
gcloud secrets create "$MAPS_SECRET" \
  --replication-policy=automatic \
  --project="$PROJECT_ID"
```

```bash
gcloud secrets create "$GEMINI_SECRET" \
  --replication-policy=automatic \
  --project="$PROJECT_ID"
```

Upload the generated Places key and the user-provided Gemini key file:

```bash
gcloud secrets versions add "$MAPS_SECRET" \
  --data-file="$MAPS_KEY_FILE" \
  --project="$PROJECT_ID"
rm -f "$MAPS_KEY_FILE"
```

```bash
test -r "$GEMINI_KEY_FILE"
gcloud secrets versions add "$GEMINI_SECRET" \
  --data-file="$GEMINI_KEY_FILE" \
  --project="$PROJECT_ID"
unset GEMINI_KEY_FILE
```

Grant the runtime identity access only to these secret resources:

```bash
gcloud secrets add-iam-policy-binding "$MAPS_SECRET" \
  --member="serviceAccount:$RUNTIME_SA" \
  --role="roles/secretmanager.secretAccessor" \
  --project="$PROJECT_ID"
```

```bash
gcloud secrets add-iam-policy-binding "$GEMINI_SECRET" \
  --member="serviceAccount:$RUNTIME_SA" \
  --role="roles/secretmanager.secretAccessor" \
  --project="$PROJECT_ID"
```

## 5. Firestore and TTL

**Cloud-changing; confirm before running.** First inspect whether the default database already exists; do not create a duplicate.

```bash
gcloud firestore databases describe \
  --database="(default)" \
  --project="$PROJECT_ID"
```

If it does not exist, create it in Native mode:

```bash
gcloud firestore databases create \
  --database="(default)" \
  --location="$REGION" \
  --type=firestore-native \
  --project="$PROJECT_ID"
```

Enable TTL on `expire_at`:

```bash
gcloud firestore fields ttls update expire_at \
  --collection-group=sessions \
  --enable-ttl \
  --project="$PROJECT_ID"
```

## 6. Cloud Run Deployment

**Cloud-changing and makes the service publicly invokable; confirm before running.** Minimum instances of 1 incur ongoing cost. `TRUSTED_HOSTS` is set for the generated `*.run.app` hostname. Secret values are mounted as environment variables; `USE_SECRET_MANAGER=false` prevents application startup from making its own Secret Manager calls.

```bash
gcloud run deploy "$SERVICE" \
  --source . \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --service-account="$RUNTIME_SA" \
  --min=1 \
  --max=5 \
  --memory=512Mi \
  --concurrency=40 \
  --timeout=60s \
  --allow-unauthenticated \
  --set-env-vars="APP_ENV=production,GCP_PROJECT_ID=${PROJECT_ID},USE_SECRET_MANAGER=false,TRUSTED_HOSTS=[\"*.run.app\"]" \
  --set-secrets="GOOGLE_MAPS_API_KEY=${MAPS_SECRET}:latest,GEMINI_API_KEY=${GEMINI_SECRET}:latest"
```

## 7. Post-Deploy Checks

These are read-only requests except for the documented temporary session created and deleted by the smoke tests.

```bash
export BASE_URL="$(gcloud run services describe "$SERVICE" \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --format="value(status.url)")"
curl -fsS "$BASE_URL/health"
curl -fsS "$BASE_URL/api/v1/scheme"
curl -fsS -H 'Content-Type: application/json' \
  -d '{"is_pregnant_or_lactating":true,"child_number":1,"categories":["BPL_RATION_CARD"],"is_govt_or_psu_employee":false}' \
  "$BASE_URL/api/v1/eligibility"
export SESSION_ID="$(python -c 'import uuid; print(uuid.uuid4())')"
curl -fsS -H 'Content-Type: application/json' \
  -d "{\"session_id\":\"$SESSION_ID\",\"message\":\"नमस्ते\"}" \
  "$BASE_URL/api/v1/chat"
curl -fsS "$BASE_URL/api/v1/places/nearby?lat=28.61&lng=77.20"
curl -fsS -H 'Content-Type: application/json' \
  -d '{"child_number":1,"benefit_amount_inr":5000,"categories":["BPL_RATION_CARD"],"required_documents":["aadhaar_mother"]}' \
  "$BASE_URL/api/v1/card"
curl -fsS -H 'Content-Type: application/json' \
  -d '{"user_utterance":"नमस्ते दीदी, मुझे योजना के बारे में जानकारी चाहिए।"}' \
  "$BASE_URL/api/v1/practice"
curl -fsS -F 'file=@/dev/null;filename=smoke.webm;type=audio/webm' \
  "$BASE_URL/api/v1/voice/transcribe"
```

Check TTS permits either synthesized audio or its documented browser-fallback status:

```bash
TTS_STATUS="$(curl -sS -o /tmp/sakhi-tts-smoke.bin -w '%{http_code}' \
  -H 'Content-Type: application/json' \
  -d '{"text":"नमस्ते","speaking_rate":0.9}' \
  "$BASE_URL/api/v1/voice/speak")"
test "$TTS_STATUS" = "200" || test "$TTS_STATUS" = "503"
rm -f /tmp/sakhi-tts-smoke.bin
```

Create and upload a neutral one-pixel image for the document-summary endpoint:

```bash
python -c 'from PIL import Image; Image.new("RGB", (1, 1), "white").save("/tmp/sakhi-smoke.jpg")'
curl -fsS -F 'file=@/tmp/sakhi-smoke.jpg;type=image/jpeg' "$BASE_URL/api/v1/vision/explain"
rm -f /tmp/sakhi-smoke.jpg
curl -fsS -X DELETE "$BASE_URL/api/v1/session?session_id=$SESSION_ID"
```

After the API checks pass, open `$BASE_URL/static/index.html` in the browser, complete the pregnancy/child/category/employment flow, verify the eligibility result and officer card, and capture desktop/mobile screenshots. The resulting live URL and the commands actually executed will be added here and to README only after the gated deployment succeeds.

## 8. Continuous Deployment

This repository uses GitHub Actions for CI/CD. The `deploy` job runs automatically on merges to `main`. It authenticates using **Workload Identity Federation**, avoiding the need for long-lived service account keys. Ensure that the GitHub repository is configured with the following secrets:
- `GCP_WIF_PROVIDER`
- `GCP_DEPLOY_SA`
- `GCP_REGION` (as a variable)
- `GCP_RUNTIME_SA` (as a variable)
