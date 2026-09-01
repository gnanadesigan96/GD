export interface CurLoadRequest {
  role_arn: string;
  external_id: string;
  s3_uri: string;
  month: string;
  region?: string;
}

export interface ServiceCost {
  service: string;
  cost: number;
}

export interface DailyCost {
  date: string;
  cost: number;
}

export interface AccountCost {
  account_id: string;
  cost: number;
}

export interface DimensionalCosts {
  product_category: string;
  resource_category: string;
  charge_type: string;
  costs: Record<string, number>;
}

export interface DrilldownRow extends DimensionalCosts {
  account_id: string;
}

export interface PartFileInfo {
  key: string;
  size_bytes: number;
}

export interface CurLoadResponse {
  billing_period: string;
  currency: string | null;
  total_cost: number;
  cost_by_service: ServiceCost[];
  cost_by_day: DailyCost[];
  cost_by_account: AccountCost[];
  file_format: string;
  part_file_count: number;
  load_time_ms: number;
  available_cost_metrics: string[];
  drilldown: DrilldownRow[];
  part_files: PartFileInfo[];
}

export interface CurJobStartedResponse {
  job_id: string;
}

export interface CurJobStatusResponse {
  status: "pending" | "done" | "error";
  result: CurLoadResponse | null;
  error: string | null;
}
