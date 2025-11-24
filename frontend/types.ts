export interface ProposalData {
  project_name: string;
  category_focus: string[];
  problem_statement: string;
  architecture_overview: string;
  technical_stack: TechnicalStack;
  workflow_steps: WorkflowStep[];
  demonstration_ui_plan: DemonstrationUiPlan;
  sponsor_alignment_pitch: SponsorAlignmentPitch;
  estimated_cost: EstimatedCost;
}

export interface TechnicalStack {
  orchestration_framework: TechComponent;
  llm_model: TechComponent;
  internal_knowledge_tool: TechComponent;
  external_knowledge_tool: TechComponent;
  integration_tools: {
    jira: TechComponent;
    github: TechComponent;
    frontend_ui: TechComponent;
  };
}

export interface TechComponent {
  name?: string;
  purpose: string;
  libraries?: string[];
}

export interface WorkflowStep {
  step_id: number;
  name: string;
  actor: string;
  details: string;
}

export interface DemonstrationUiPlan {
  design_tool: string;
  key_panels: { name: string; content: string }[];
}

export interface SponsorAlignmentPitch {
  mongodb_win: string;
  tavily_win: string;
  overall_win: string;
}

export interface EstimatedCost {
  mongodb_atlas: string;
  tavily_api: string;
  llm_api: string;
  total_estimated_poc_cost: string;
}

// Visual Types
export interface NodePosition {
  id: string;
  x: number; // Percentage 0-100
  y: number; // Percentage 0-100
  label: string;
  type: 'trigger' | 'core' | 'knowledge' | 'execution' | 'ui';
  icon: string;
  description: string;
  tech?: TechComponent; // Linked tech data
}

export interface Edge {
  from: string;
  to: string;
  label?: string;
  activeInStep?: number[];
}
