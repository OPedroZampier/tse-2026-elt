# Power BI private update: operations and validation

The weekly workflow is in the main branch. It is configured to follow a successful scheduled or manually started TSE pipeline on main. A complete run of this chained workflow on main has not yet been verified.

## Validation status

- A guarded end-to-end candidate test uploaded and verified a batch, backed up the previous manifest and switched to the new manifest. The tested batch contained 19 datasets, 55 parts and 3,757,926 rows.
- The Power Automate flow triggered a refresh of the validation semantic model. Power BI completed it with a warning: an expression referring to multiple columns could not be converted to a scalar value. Investigate the model warning and validate the visuals before treating the report as fully verified.
- The published report uses the validation semantic model. Confirm external access before sharing it with a recruiter.
- Monitor the next eligible main-branch run end to end, including the Kaggle publication, OneDrive activation, Power Automate trigger and Power BI refresh history.

The workflow collects fresh TSE files again, so the Power BI snapshot can differ from the Kaggle snapshot if the TSE changes files between runs. It validates the new files, verifies every private upload, saves and verifies the prior manifest in the new private batch, and then attempts a guarded manifest switch.

The guard checks the previous manifest and its ETag before committing. The final check and commit are not an atomic compare-and-swap, so avoid manual or parallel manifest edits during an update. The GitHub concurrency group serializes the jobs that use it but cannot prevent edits made outside those jobs.

The Microsoft delegated application has broad access to the university OneDrive; the code writes only within the project folder. The delegated token and GitHub token must remain Actions secrets, never repository variables or files in the repository. University policy, token expiry or revoked consent can interrupt the workflow.

If activation reports an uncertain result, do not blindly retry: inspect the current manifest, the private backup in the batch's `previous_manifest` folder, and Power BI refresh history before choosing whether to restore or continue.
