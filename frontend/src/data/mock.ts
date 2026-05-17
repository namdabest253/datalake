// Mock data for the React frontend. Swap to a fetch-based API client
// (src/api/*.ts) once the Python backend exposes HTTP endpoints.

export type ComplianceStatus = "clean" | "restricted" | "unclear";

export type StreamItem = {
  id: string;
  filename: string;
  contentType: string;
  status: "Ready" | "Extracting" | "Failed" | "Queued";
  iconName: string;
};

export const STREAM_ITEMS: StreamItem[] = [
  {
    id: "1",
    filename: "arXiv:2405.0123.pdf",
    contentType: "Research Paper",
    status: "Ready",
    iconName: "description",
  },
  {
    id: "2",
    filename: "clinical_trial_d4.csv",
    contentType: "Tabular Data",
    status: "Extracting",
    iconName: "dataset",
  },
  {
    id: "3",
    filename: "unstructured_log_v9.txt",
    contentType: "Raw Text",
    status: "Failed",
    iconName: "warning",
  },
  {
    id: "4",
    filename: "mri_scan_0042.dcm",
    contentType: "Medical Imaging",
    status: "Queued",
    iconName: "image",
  },
  {
    id: "5",
    filename: "nsf_grant_b3924.json",
    contentType: "Grant Proposal",
    status: "Ready",
    iconName: "article",
  },
  {
    id: "6",
    filename: "arXiv:2405.0456.pdf",
    contentType: "Research Paper",
    status: "Extracting",
    iconName: "description",
  },
];

export type CatalogRow = {
  id: string;
  name: string;
  owner: string;
  compliance: ComplianceStatus;
  complianceLabel: string;
  score: number;
  iconName: string;
  contentType?: string;
};

export const CATALOG_ROWS: CatalogRow[] = [
  {
    id: "1",
    name: "Quantum Cryptography Post-Doctoral Thesis",
    owner: "MIT / Dr. Alan Turing",
    compliance: "clean",
    complianceLabel: "Clean",
    score: 94,
    iconName: "description",
  },
  {
    id: "2",
    name: "Patient Genomic Sequencing Cohort A",
    owner: "Stanford Med / Dr. Chen",
    compliance: "restricted",
    complianceLabel: "Restricted",
    score: 88,
    iconName: "description",
  },
  {
    id: "3",
    name: "Autonomous Vehicle Sensor Logs Q3",
    owner: "UC Berkeley / AutoLab",
    compliance: "clean",
    complianceLabel: "Clean",
    score: 98,
    iconName: "dataset",
  },
  {
    id: "4",
    name: "CRISPR-Cas9 Off-Target Analysis",
    owner: "Harvard / Genetics Dept",
    compliance: "clean",
    complianceLabel: "Clean",
    score: 91,
    iconName: "science",
  },
  {
    id: "5",
    name: "FERPA-Adjacent Course Outcomes 2024",
    owner: "U-Chicago / Registrar",
    compliance: "restricted",
    complianceLabel: "FERPA",
    score: 23,
    iconName: "school",
  },
];

export const RECENT_UPLOADS = [
  {
    id: "1",
    name: "Research_Archive_2024.zip",
    files: 15000,
    status: "Processing",
    progress: 42,
    iconName: "folder_zip",
  },
  {
    id: "2",
    name: "NSF_Grants_Biology.folder",
    files: 5000,
    status: "Completed",
    progress: 100,
    iconName: "folder",
  },
  {
    id: "3",
    name: "Compliance_Edge_Cases.zip",
    files: 30,
    status: "Completed",
    progress: 100,
    iconName: "folder_zip",
  },
];

export const EVAL_DIMENSIONS = [
  { name: "Methodology Extraction", winRate: 82 },
  { name: "Novelty Claim Accuracy", winRate: 94 },
  { name: "Ownership / Citation Accuracy", winRate: 75 },
  { name: "Compliance Flag Recall", winRate: 88 },
];

export const SAMPLE_EXPORT_RECORD = `{
  "id": "doc_8f7a9c2b_physics_001",
  "corpus_domain": "Physics / Quantum Mechanics",
  "content_hash": "a1b2c3d4e5f6g7h8i9j0",
  "methodology": {
    "extraction_agent": "Wafer-Qwen-3.5-397B",
    "cleaning_pipeline": ["Remove_HTML", "Normalize_Equations_LaTeX"],
    "token_count": 4096
  },
  "ownership": {
    "source_institution": "European Council for Nuclear Research",
    "license": "CC-BY-4.0",
    "clearance_level": "Public_Domain"
  },
  "quality_metrics": {
    "judge_model_score": 0.96,
    "hallucination_risk": 0.02,
    "toxicity_flag": false
  },
  "text_payload": "The observable universe..."
}`;
