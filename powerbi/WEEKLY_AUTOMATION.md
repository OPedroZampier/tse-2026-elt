# Power BI private update: deployment checklist

This is a candidate configuration, not an enabled production schedule.

1. Wait for the guarded test to finish and confirm that the manifest switch succeeded.
2. Refresh the validation semantic model in Power BI and compare its totals with the independently verified metrics for the same batch. Inspect refresh errors and visuals.
3. Test the Power Automate trigger and confirm it refreshes the intended semantic model.
4. Confirm the production report's semantic model and credentials before changing the flow target. Keep the validation model and the previous batch available for rollback.
5. Review and deploy the weekly workflow only after the previous checks pass.

The weekly candidate waits for a successful scheduled or manually started TSE pipeline on the repository's main branch. It collects fresh TSE files again, so the Power BI snapshot can differ from the Kaggle snapshot if the TSE changes files between runs. It validates the new files, verifies every private upload, saves and verifies the prior manifest in the new private batch, and then attempts a guarded manifest switch.

The guard checks the previous manifest and its ETag before committing. The final check and commit are not an atomic compare-and-swap, so avoid manual or parallel manifest edits during an update. The GitHub concurrency group serializes the jobs that use it but cannot prevent edits made outside those jobs.

The Microsoft delegated application has broad access to the university OneDrive; the code writes only within the project folder. The delegated token and GitHub token must remain Actions secrets, never repository variables or files in the repository. University policy, token expiry or revoked consent can interrupt the workflow.

If activation reports an uncertain result, do not blindly retry: inspect the current manifest, the private backup in the batch's previous_manifest folder, and Power BI refresh history before choosing whether to restore or continue.
