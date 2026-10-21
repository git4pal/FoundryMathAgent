# Deploy FoundryMathAgent To Microsoft Foundry

This guide registers the **prompt-agent definition** in a Microsoft Foundry
project. The Python CLI remains the function executor. No container, web server,
App Service, or hosted-agent runtime is provisioned by this repository.

## 1. Prerequisites

- An Azure subscription and permission to use or create a Foundry resource/project.
- Python 3.10+ and the [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli).
- Permission to deploy models, or an administrator who can deploy the model for you.
- A region and subscription with access and quota for the requested model.

Model/API calls can incur charges. Local unit tests do not call Azure.
No cloud resources have been created by generating this project.

## 2. Select Or Create A Foundry Project

1. Open [Microsoft Foundry](https://ai.azure.com/).
2. Select your existing project. If you do not have one, create a Foundry
   resource and project using the portal's project-creation flow. Select the
   intended subscription, resource group, region, and project name.
3. Use a current Foundry project backed by a Foundry resource, not a legacy
   hub-only project requiring a connection string.
4. Copy the **project endpoint** from the project's overview/settings page.

Expected format:

```text
https://<resource>.services.ai.azure.com/api/projects/<project>
```

Do not use `https://<resource>.openai.azure.com/`, a portal URL, an ARM resource
ID, or a legacy connection string in place of the project endpoint.

## 3. Deploy The Model As gpt-5.4-nano

1. In your project, open the model catalog/deployment area.
2. Locate `gpt-5.4-nano` and verify that your region/subscription supports it.
3. Deploy it with the **deployment name** `gpt-5.4-nano`.
4. Choose an available deployment type and appropriate capacity within quota.
5. Wait until the deployment is ready. Confirm it supports Responses, function
   calling, strict tool schemas, and required tool selection.

The code uses a **deployment name**, not a catalog identifier. Model availability
and regional quota have not been verified for your tenant. If the requested
model is unavailable, request access/quota or select a supported region. Do not
silently substitute another model. A different tool-capable model can be used
only after an explicit decision, by changing `FOUNDRY_MODEL_NAME` and registering
a new agent version.

## 4. Grant Access And Sign In

1. In Azure portal IAM for the Foundry resource/project, grant your executing
   user an appropriate role, normally **Azure AI User**, at the required scope.
   Agent creation and model invocation must both be permitted. Have your
   administrator verify effective roles and any additional model-deployment
   management permissions; subscription Contributor alone may not grant all
   data-plane permissions.
2. Allow role assignments time to propagate.
3. Run these commands yourself in a terminal:

```bash
az login
az account set --subscription "<subscription-id>"
az account show --query "{subscription:name,tenant:tenantId}" -o table
```

For another tenant, use `az login --tenant <tenant-id>`. Never put a password or
access token into source code or `.env`. `DefaultAzureCredential` also considers
environment credentials and managed identity; stale `AZURE_CLIENT_ID`,
`AZURE_TENANT_ID`, or `AZURE_CLIENT_SECRET` values can select a different identity.

## 5. Prepare Python

From the repository root on macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip show azure-ai-projects
python -m unittest discover -s tests -v
cp .env.example .env
```

On Windows:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
Copy-Item .env.example .env
```

The SDK is pinned to `azure-ai-projects==2.9.0`. Do not substitute 1.x examples
using threads/runs for the Responses-based API used here.

## 6. Set Project Configuration

Edit `.env`:

```dotenv
FOUNDRY_PROJECT_ENDPOINT=https://<resource>.services.ai.azure.com/api/projects/<project>
FOUNDRY_MODEL_NAME=gpt-5.4-nano
FOUNDRY_AGENT_VERSION=
```

Replace the endpoint placeholders. Leave the version empty for the initial
registration. Existing shell variables override `.env`; clear stale values first.

## 7. Register The Agent

```bash
python main.py --deploy
```

Expected output resembles:

```text
Registered FoundryMathAgent version 1
Set FOUNDRY_AGENT_VERSION=1 in .env
```

The actual version can differ. This creates a version with the name
`FoundryMathAgent`, the requested model, strict instructions, no fixed tool choice,
and five function tools: `add`, `subtract`, `multiply`, `divide`, `reject_request`.
The client requires a tool on the initial request and disables tools on the
continuation. Do not lock `tool_choice` in the agent definition: Foundry requires
request-level choices to match it, which would prevent this two-stage workflow.
No web-search or Bing tool is attached. Each deployment creates a version;
registration does not upload or execute Python functions in Azure.

Enter the printed version in `.env`, for example:

```dotenv
FOUNDRY_AGENT_VERSION=1
```

In Foundry's agent list, verify the agent/version and deployment reference.
Use the CLI, not the portal playground alone, for end-to-end function execution
and application-enforced validation.

## 8. Run Live Smoke Tests

These commands invoke your model and can incur usage charges:

```bash
python main.py --prompt "what is 2 plus 5" --verbose
python main.py --prompt "2+5"
python main.py --prompt "subtract 3 from 10"
python main.py --prompt "6*7"
python main.py --prompt "9/2"
python main.py --prompt "tell me a joke"
python main.py --prompt "search the web for 2+5"
python main.py --prompt "1/0"
```

Expected stdout, in order: `7`, `7`, `7`, `42`, `4.5`, followed by the exact
fallback for each of the final three commands. Verbose mode logs the requested
tool name and acceptance decision on stderr. Confirm that the correct arithmetic
tools are used and the unsupported queries do not return an answer from model prose.

Start interactive mode with `python main.py`. Press F5 in VS Code for terminal
debugging. Each prompt is independent; this sample does not implement chat memory.

## 9. Updates And Rollback

1. Make code/instruction changes and rerun the offline tests.
2. Run `python main.py --deploy` to register a new immutable version.
3. Set `FOUNDRY_AGENT_VERSION` to the new version and rerun live smoke tests.
4. Keep the previous version until the new version is verified.

For rollback, restore the matching application revision and previous version
number. Startup validation rejects a remote definition that differs from the
local schemas, instructions, or deployment reference. An old version is not a
compatible rollback target after changing those fields unless the code is also restored.

## 10. Running Without Your Laptop

The registered prompt agent alone cannot execute the Python functions. To run
continuously, operate this Python application on a host you manage, or extend it
into a hosted agent/API with the same validation boundary. That hosting is outside
this sample's deployment. Use managed identity rather than interactive Azure CLI
login for an Azure-hosted process; grant that identity the required Foundry roles.
Do not expose direct model/agent access as an alternative to the guarded client.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Missing configuration, exit code 2 | Endpoint and version in `.env`; run `--deploy` before setting version |
| 401/authentication failure | Azure CLI login, tenant and selected credential source |
| 403 | Effective identity, project/resource RBAC and propagation |
| 404/model not found | Project endpoint, model deployment **name**, agent name and pinned version |
| Unsupported parameter/tool schema | Pinned SDK and model support for required strict function calling |
| `ToolChoice must match the agent's tool_choice` | Run `python main.py --deploy` with the corrected definition and set `FOUNDRY_AGENT_VERSION` to its printed version; the old version fixes tool choice to `required` |
| Definition mismatch | Register current code and pin its printed version; do not attach search tools |
| Valid arithmetic returns fallback | Use documented grammar and `--verbose`; wrong model routing is rejected |
| No tool result in portal | Functions run in this Python client, not in the portal |
| Throttling/429 or timeout | Model capacity/quota, service status, network and retry policy |

The application intentionally avoids dumping response bodies or authentication
details on errors. For deeper diagnostics, inspect authorized Foundry monitoring
and use a local debugger; protect any prompts or response data in diagnostic logs.

## Cleanup

Remove unused versions in the Foundry portal, or use the SDK's
`project.agents.delete_version(agent_name="FoundryMathAgent", agent_version="<version>")`
from an authenticated project client. Remove the agent only after confirming
no other clients use it. Deleting an agent does not delete the model deployment,
Foundry resource, or response data. Review service retention settings separately.

Delete a model deployment or resource group only if it was dedicated to this
sample and no other workload uses it. Model deployment capacity may incur costs
independently of whether this CLI is running.