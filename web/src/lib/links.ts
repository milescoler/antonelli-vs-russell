// Links from the dashboard out to the analytical write-up that backs it.
// Absolute github.com URLs on purpose: the Pages build is served under
// /antonelli-vs-russell/, so repo-relative paths (../docs/...) don't resolve.
const REPO = 'https://github.com/milescoler/antonelli-vs-russell'

export const STUDY_LINKS = {
  caseStudy: `${REPO}/blob/main/docs/case_study.md`,
  notebooks: `${REPO}/tree/main/notebooks`,
  source: REPO,
} as const
