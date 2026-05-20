# Graph Report - .  (2026-05-19)

## Corpus Check
- Corpus is ~21,582 words - fits in a single context window. You may not need a graph.

## Summary
- 419 nodes · 452 edges · 63 communities (36 shown, 27 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 48 edges (avg confidence: 0.78)
- Token cost: 45,250 input · 8,500 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Core RAG and Generation Pipeline|Core RAG and Generation Pipeline]]
- [[_COMMUNITY_API Endpoint Controllers|API Endpoint Controllers]]
- [[_COMMUNITY_Main App & RAG Indexer|Main App & RAG Indexer]]
- [[_COMMUNITY_Next.js Pages & Approval Frontend|Next.js Pages & Approval Frontend]]
- [[_COMMUNITY_Next.js Package Dependencies|Next.js Package Dependencies]]
- [[_COMMUNITY_Compliance Engine & Regulation Matcher|Compliance Engine & Regulation Matcher]]
- [[_COMMUNITY_Shadcn Component Configuration|Shadcn Component Configuration]]
- [[_COMMUNITY_Compliance Test Suites|Compliance Test Suites]]
- [[_COMMUNITY_TypeScript Project Configuration|TypeScript Project Configuration]]
- [[_COMMUNITY_Document Parsing and AML PDF Processing|Document Parsing and AML PDF Processing]]
- [[_COMMUNITY_Graph & DB Core Infrastructure|Graph & DB Core Infrastructure]]
- [[_COMMUNITY_API Workflow and Models|API Workflow and Models]]
- [[_COMMUNITY_App Page Layouts & Panels|App Page Layouts & Panels]]
- [[_COMMUNITY_RAG LLM Content Services|RAG LLM Content Services]]
- [[_COMMUNITY_Frontend Plan Scorecard|Frontend Plan Scorecard]]
- [[_COMMUNITY_Module Validators Py|Module: Validators Py]]
- [[_COMMUNITY_Module App Layout Inter|Module: App Layout Inter]]
- [[_COMMUNITY_Module Architecture High Level Arc...|Module: Architecture High Level Arc...]]
- [[_COMMUNITY_Module Seed Graph Py|Module: Seed Graph Py]]
- [[_COMMUNITY_Module Myapp Next Config|Module: Myapp Next Config]]
- [[_COMMUNITY_Module Architecture System Purpose|Module: Architecture System Purpose]]
- [[_COMMUNITY_Module Database Engine|Module: Database Engine]]
- [[_COMMUNITY_Module Eslint Config Mjs|Module: Eslint Config Mjs]]
- [[_COMMUNITY_Module Agents Rules|Module: Agents Rules]]
- [[_COMMUNITY_Module Next Config Js|Module: Next Config Js]]
- [[_COMMUNITY_Module Postcss Config Mjs|Module: Postcss Config Mjs]]
- [[_COMMUNITY_Module Rag Document Parser Rationa...|Module: Rag Document Parser Rationa...]]
- [[_COMMUNITY_Module Services Roadmap Service Ra...|Module: Services Roadmap Service Ra...]]
- [[_COMMUNITY_Module Services Roadmap Service Ra...|Module: Services Roadmap Service Ra...]]
- [[_COMMUNITY_Module Services Roadmap Service Ra...|Module: Services Roadmap Service Ra...]]
- [[_COMMUNITY_Module Services Simulation Service...|Module: Services Simulation Service...]]
- [[_COMMUNITY_Module Services Quiz Service Ratio...|Module: Services Quiz Service Ratio...]]
- [[_COMMUNITY_Module Dockercompose Postgres|Module: Dockercompose Postgres]]
- [[_COMMUNITY_Module Dockercompose Neo4J|Module: Dockercompose Neo4J]]
- [[_COMMUNITY_Module Llm Content Summarize Text|Module: Llm Content Summarize Text]]
- [[_COMMUNITY_Module Services Validators Validat...|Module: Services Validators Validat...]]
- [[_COMMUNITY_Module Config|Module: Config]]
- [[_COMMUNITY_Module Tsconfig Config|Module: Tsconfig Config]]
- [[_COMMUNITY_Module Eslint Config Config|Module: Eslint Config Config]]
- [[_COMMUNITY_Module Readme Doc|Module: Readme Doc]]
- [[_COMMUNITY_Module App Layout Rootlayout|Module: App Layout Rootlayout]]
- [[_COMMUNITY_Module Public File Logo|Module: Public File Logo]]
- [[_COMMUNITY_Module Public Vercel Logo|Module: Public Vercel Logo]]
- [[_COMMUNITY_Module Public Next Logo|Module: Public Next Logo]]
- [[_COMMUNITY_Module Public Globe Logo|Module: Public Globe Logo]]
- [[_COMMUNITY_Module Public Window Logo|Module: Public Window Logo]]

## God Nodes (most connected - your core abstractions)
1. `KnowledgeIndexBuilder` - 21 edges
2. `compilerOptions` - 16 edges
3. `TrainingPlanGenerator` - 16 edges
4. `governed_llm_call()` - 15 edges
5. `build_compliance_training_plan()` - 14 edges
6. `DocumentParser` - 12 edges
7. `RoadmapService` - 8 edges
8. `governed_llm_call` - 7 edges
9. `Home Component` - 7 edges
10. `tailwind` - 6 edges

## Surprising Connections (you probably didn't know these)
- `DocumentParser` --parses--> `EU AMLR 2024/1624 PDF`  [EXTRACTED]
  backend/app/rag/document_parser.py → /Users/viku/Dev_Projects/vidda-2/ai-compliance-engine/backend/data/documents/compliance/eu_amlr_1624.pdf
- `RoadmapService` --references--> `validate_governance_boundaries`  [INFERRED]
  backend/app/services/roadmap_service.py → /Users/viku/Dev_Projects/vidda-2/ai-compliance-engine/backend/app/services/validators.py
- `test_neo4j_connection_and_traversal()` --calls--> `next`  [INFERRED]
  backend/tests/test_compliance.py → frontend/my-app/package.json
- `test_generate_training_endpoint_e2e()` --calls--> `next`  [INFERRED]
  backend/tests/test_compliance.py → frontend/my-app/package.json
- `get_legal_evidence()` --calls--> `KnowledgeIndexBuilder`  [INFERRED]
  backend/app/services/roadmap_service.py → backend/app/rag/knowledge_index.py

## Hyperedges (group relationships)
- **compliance_generation_pipeline** — architecture_primary_flow, backend_app_api_routes_compliance_generate_plan, backend_app_graph_neo4j_client_driver, backend_app_rag_knowledge_index_knowledgeindexbuilder [INFERRED 0.95]
- **database_infrastructure_layer** — dockercompose_postgres, dockercompose_neo4j, backend_app_db_database_engine, backend_app_graph_neo4j_client_driver [INFERRED 0.95]
- **governed_generation_flow** — services_llm_service_governedllmcall, services_validators_validategovernanceboundaries, services_llm_service_systemmentalmodel [INFERRED]
- **compliance_path_assembly** — services_compliance_engine_buildcompliancetrainingplan, services_roadmap_service_roadmapservice, services_generator_trainingplangenerator [INFERRED]
- **e2e_compliance_testing** — tests_test_compliance_compliancetestsuite, services_compliance_engine_buildcompliancetrainingplan, services_roadmap_service_roadmapservice [INFERRED]
- **Training Plan Generation Flow** — frontend_myapp_components_upload_inputsection, frontend_myapp_app_page_home, frontend_myapp_components_planscorecard_planscorecard, frontend_myapp_components_approvalworkflow_approvalworkflow [EXTRACTED 1.00]

## Communities (63 total, 27 thin omitted)

### Community 0 - "Core RAG and Generation Pipeline"
Cohesion: 0.05
Nodes (36): evaluate_plan_endpoint(), extract_role(), Extract role, responsibilities, and risks from free text — single LLM call only., Retrieve details for plan quality scorecard, Exception, build_compliance_training_plan, get_governed_paths, _build_scorecard() (+28 more)

### Community 1 - "API Endpoint Controllers"
Cohesion: 0.06
Nodes (32): compliance_explainability(), explainability_endpoint(), generate_quiz_endpoint(), generate_simulation_endpoint(), generate_training(), get_plan(), get_plans(), get_regulations() (+24 more)

### Community 2 - "Main App & RAG Indexer"
Cohesion: 0.09
Nodes (19): lifespan(), Warm up the embedding model before any user request arrives.     Moves the 1.5s, DocumentChunk, Represents a chunk of document content with rich legal metadata, create_embedding(), KnowledgeChunk, KnowledgeIndexBuilder, main() (+11 more)

### Community 3 - "Next.js Pages & Approval Frontend"
Cohesion: 0.08
Nodes (17): Module, QUARTERS, WorkflowData, Notification, Props, REVISION_STAGES, Stage, Plan (+9 more)

### Community 4 - "Next.js Package Dependencies"
Cohesion: 0.07
Nodes (28): dependencies, axios, class-variance-authority, lucide-react, radix-ui, react, react-dom, react-dropzone (+20 more)

### Community 5 - "Compliance Engine & Regulation Matcher"
Cohesion: 0.11
Nodes (24): build_compliance_training_plan(), _build_regulation_ref(), _competency_from_control(), _deterministic_description(), _extract_article_num(), find_regulations_for_risks(), generate_module_description(), generate_module_name() (+16 more)

### Community 6 - "Shadcn Component Configuration"
Cohesion: 0.09
Nodes (21): aliases, components, hooks, lib, ui, utils, iconLibrary, menuAccent (+13 more)

### Community 7 - "Compliance Test Suites"
Cohesion: 0.10
Nodes (21): next, Verify that targeting quiz generation directly returns compliant response, Verify that targeting simulation generation directly returns compliant response, Verify explainability compliance trace returns traversed graph mapping paths, Verify that Compliance Analyst produces deterministic roadmap mapping to all 4 q, Verify that POST /workflow/run uses the Neo4j compliance graph to build 4-quarte, Verify PostgreSQL and pgvector database connection and table integrity, Verify Neo4j driver connection and graph traversal logic for seed KYC Analyst (+13 more)

### Community 8 - "TypeScript Project Configuration"
Cohesion: 0.10
Nodes (19): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+11 more)

### Community 9 - "Document Parsing and AML PDF Processing"
Cohesion: 0.13
Nodes (12): EU AMLR 2024/1624 PDF, _detect_legal_header(), DocumentParser, _infer_section_from_content(), Document parser for compliance documents (HTML, PDF, TXT)  Phase 5 upgrade: - Ar, Parse PDF and create chunks with article/recital metadata., Parse HTML document and create chunks with article/recital metadata., Normalize whitespace and strip control characters. (+4 more)

### Community 10 - "Graph & DB Core Infrastructure"
Cohesion: 0.12
Nodes (17): Neo4j Governance Graph Concept, Compliance Engine Primary Flow, compliance_generate_plan Router Endpoint, get_roles Router Endpoint, suggest_controls Router Endpoint, suggest_risks Router Endpoint, SessionLocal DB Session Factory, Neo4j Driver Singleton (+9 more)

### Community 11 - "API Workflow and Models"
Cohesion: 0.20
Nodes (15): compliance_generate_plan(), PRIMARY ENDPOINT — Core compliance training plan generator.      Input:, Orchestrates RAG context search and generates a persistent 1-year training plan, Revise and update an existing plan based on user comments/feedback, revise_plan_endpoint(), workflow_run(), Base, Control (+7 more)

### Community 12 - "App Page Layouts & Panels"
Cohesion: 0.20
Nodes (11): Home Component, ModuleRow Component, normalise Function, ApprovalWorkflow Component, CircleScore Component, PlanScorecard Component, SavedPlansPanel Component, timeAgo Helper (+3 more)

### Community 13 - "RAG LLM Content Services"
Cohesion: 0.22
Nodes (9): build_module_from_chunk(), generate_quiz_from_text(), generate_training_module(), LLM Content Generation utilities for compliance training - Summarize regulation/, Return a concise summary for the provided text using the LLM.     This delegates, Generate a training module skeleton from provided source text.      Returns a di, Generate a short quiz (questions + correct answers) from a text chunk.     Retur, Produce a training module dict for a single chunk.     This will create a summar (+1 more)

### Community 14 - "Frontend Plan Scorecard"
Cohesion: 0.36
Nodes (7): CircleScore(), Dimension, PlanScorecard(), Props, Scorecard, scoreColor(), scoreLabel()

### Community 15 - "Module: Validators Py"
Cohesion: 0.29
Nodes (6): Check that all regulation references in output exist in known set.      Args:, Check LLM output for potential governance violations.      Scans for:     - Hall, Validate that a parsed JSON output matches expected schema.      Args:         d, validate_governance_boundaries(), validate_no_hallucinated_regulations(), validate_structured_output()

### Community 16 - "Module: App Layout Inter"
Cohesion: 0.40
Nodes (3): inter, jetbrains, metadata

### Community 18 - "Module: Architecture High Level Arc..."
Cohesion: 0.67
Nodes (3): High Level Architecture Summary, FastAPI APIRouter, FastAPI App Object

### Community 20 - "Module: Myapp Next Config"
Cohesion: 0.67
Nodes (3): Next.js Config, App Dependencies, PostCSS Config

## Knowledge Gaps
- **125 isolated node(s):** `config`, `nextConfig`, `name`, `version`, `private` (+120 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **27 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `KnowledgeIndexBuilder` connect `Main App & RAG Indexer` to `Core RAG and Generation Pipeline`, `Document Parsing and AML PDF Processing`, `Compliance Engine & Regulation Matcher`, `API Endpoint Controllers`?**
  _High betweenness centrality (0.225) - this node is a cross-community bridge._
- **Why does `create_embedding()` connect `Main App & RAG Indexer` to `Compliance Test Suites`?**
  _High betweenness centrality (0.195) - this node is a cross-community bridge._
- **Why does `test_embedding_generation()` connect `Compliance Test Suites` to `Main App & RAG Indexer`?**
  _High betweenness centrality (0.185) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `KnowledgeIndexBuilder` (e.g. with `DocumentParser` and `DocumentChunk`) actually correct?**
  _`KnowledgeIndexBuilder` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `TrainingPlanGenerator` (e.g. with `KnowledgeIndexBuilder` and `extract_role()`) actually correct?**
  _`TrainingPlanGenerator` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `governed_llm_call()` (e.g. with `generate_summary()` and `generate_module_name()`) actually correct?**
  _`governed_llm_call()` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `build_compliance_training_plan()` (e.g. with `compliance_generate_plan()` and `KnowledgeIndexBuilder`) actually correct?**
  _`build_compliance_training_plan()` has 2 INFERRED edges - model-reasoned connections that need verification._