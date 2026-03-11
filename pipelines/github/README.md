# GitHub Actions Pipelines

GitHub Actions workflows for automatically versioning and deploying Itential Platform assets. These workflows execute the shared scripts in `pipelines/scripts/` to handle version bumping and asset deployment.

## Workflows

### Automatic RC Tagging (`auto-rc-tag.yml`)

Triggers when a pull request from `develop` is merged into `main`. It automatically:

1. Determines the version bump type by scanning commit messages using [Conventional Commits](https://www.conventionalcommits.org/)
   - `feat!:` or `BREAKING CHANGE:` &rarr; **major** bump
   - `feat:` &rarr; **minor** bump
   - All other commits &rarr; **patch** bump
2. Creates and pushes an annotated release candidate tag (e.g., `v1.1.0-rc.1`)

### Asset Promotion (`asset-promotion.yml`)

Triggers on any tag push matching `v*`. The tag determines the target environment:

| Tag pattern | Example | Target environment |
| --- | --- | --- |
| Contains `-rc` | `v1.1.0-rc.1` | Staging |
| No `-rc` suffix | `v1.1.0` | Production |

The workflow runs `.github/scripts/deploy.py` which connects to the target Itential Platform instance and imports all discovered assets.

## Setup

### Prerequisites

- A GitHub repository using this template structure
- Two Itential Platform instances (staging and production) with service account credentials
- A GitHub Personal Access Token (PAT) with permission to push tags

### 1. Copy Workflow and Script Files

Copy the workflow files from this directory into your repository's `.github/workflows/` directory, and copy the shared scripts from `pipelines/scripts/` into `.github/scripts/`:

```bash
mkdir -p <path-to-your-repo>/.github/workflows <path-to-your-repo>.github/scripts
cp pipelines/github/*.yml <path-to-your-repo>/.github/workflows/
cp pipelines/scripts/* <path-to-your-repo>/.github/scripts/
```

> **Note:** The workflows reference scripts at `.github/scripts/` by default. If you place them elsewhere, update the script paths in each workflow file accordingly.

### 2. Configure GitHub Environments

Create two [GitHub environments](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment) — `staging` and `production` — each with the following secrets and variables:

| Type | Name | Description |
| --- | --- | --- |
| Secret | `PLATFORM_HOST` | Itential Platform instance hostname |
| Secret | `PLATFORM_CLIENT_ID` | Service account client ID |
| Secret | `PLATFORM_CLIENT_SECRET` | Service account client secret |
| Variable | `PROJECT_MEMBERS` | JSON array of project members (see below) |

### 3. Create Repository Secret

Create a repository-level secret for the auto-rc-tag workflow:

| Type | Name | Description |
| --- | --- | --- |
| Secret | `RC_TAG_PAT` | GitHub PAT with permission to push tags |

### 4. Configure Project Members

The `PROJECT_MEMBERS` variable is a JSON array that controls who gets assigned to imported Studio projects. It supports two member types:

```json
[
  { "type": "account", "username": "user@example.com", "role": "owner" },
  { "type": "group", "name": "network-ops", "role": "operator" }
]
```

## Deploying

### To Staging (automatic)

1. Commit changes to `develop` using [Conventional Commits](https://www.conventionalcommits.org/) (e.g., `feat: add vlan provisioning use case`)
2. Open a PR from `develop` to `main` and merge it
3. The `auto-rc-tag` workflow creates an RC tag, which triggers deployment to staging

### To Staging (manual)

```bash
git tag v1.1.0-rc.1
git push origin v1.1.0-rc.1
```

### To Production

After validating in staging, create a release in GitHub:

1. Go to **Releases** > **Draft a new release** in your GitHub repository
2. Create a new tag using the version number (e.g., `v1.1.0`) — do not include the `-rc` suffix
3. Set the target branch to `main`
4. Add release notes describing the changes
5. Click **Publish release**

Publishing the release pushes the tag, which triggers the production deployment.

## Running the Deploy Script Locally

```bash
export HOST="<platform-hostname>"
export CLIENT_ID="<client-id>"
export CLIENT_SECRET="<client-secret>"
export PROJECT_MEMBERS='[{"type":"account","username":"user@example.com","role":"admin"}]'

pip install git+https://github.com/Itential/asyncplatform.git
python pipelines/scripts/deploy.py <Staging|Production>
```
