# Operational Data Contracts

## Purpose

This document defines the business-first data contracts for the approved operational source model used by the Fabric Field Operations Intelligence Platform. It is the authoritative business definition of what each source entity must look like, how entities relate, and what conditions must be satisfied before data is accepted for downstream use.

This document is not the Gold star schema. It governs the source model only. Its purpose is to ensure that operational data is complete, consistent, traceable, and suitable for Phase 10 synthetic data generation and Silver validation.

## Contract Principles

- The contracts are written for business stakeholders and are technology-independent.
- The approved source grain remains unchanged.
- Business keys are immutable and must not be reassigned or overwritten.
- Required fields cannot be null.
- Foreign keys must resolve to an existing record in the referenced entity.
- Historical business events must be preserved.
- Silver may standardize and validate data, but it must not invent missing business values or silently correct source data.
- Every validation rule has an enforcement level: Hard Reject, Warn and Flag, or Informational.
- The source model must preserve lineage for schedule changes and other historical events.

## Region Contract

- Business Purpose: Represents the operating region used to group offices and field activity.
- Grain: One row per region.
- Business Key: Region code, supplied by the source system and immutable.
- Candidate Primary Key: Region identifier.
- Required Fields: region_code, region_name.
- Nullable Fields: region_description.
- Foreign Keys: None.
- Accepted Values or Controlled Domains: region_code should be a stable business code and region_name should be non-blank.
- Validation Rules:

| Rule | Enforcement |
| --- | --- |
| Region code is required and cannot be null. | Hard Reject |
| Duplicate region business keys are not allowed. | Hard Reject |
| Region name must be populated with a meaningful value. | Warn and Flag |

- Update Behavior: Region master values are updated only when the business definition changes; historical business meaning must be preserved.

## Office Contract

- Business Purpose: Represents a business office that belongs to a region and serves as the home office for employees and crews.
- Grain: One row per office.
- Business Key: Office code, supplied by the source system and immutable.
- Candidate Primary Key: Office identifier.
- Required Fields: office_code, office_name, region_id.
- Nullable Fields: office_description.
- Foreign Keys: region_id -> Region.
- Accepted Values or Controlled Domains: office_code and office_name should be unique within the operating context.
- Validation Rules:

| Rule | Enforcement |
| --- | --- |
| Office code is required and cannot be null. | Hard Reject |
| Office must reference a valid region. | Hard Reject |
| Duplicate office business keys are not allowed. | Hard Reject |
| Missing office name is a warning. | Warn and Flag |

- Update Behavior: Office definitions remain stable; updates should not change the historical identity of the office.

## Employee Contract

- Business Purpose: Represents a workforce member who may be assigned to crews or serve as a crew lead.
- Grain: One row per employee.
- Business Key: Employee number, supplied by the source system and immutable.
- Candidate Primary Key: Employee identifier.
- Required Fields: employee_number, employee_name, home_office_id, employment_status.
- Nullable Fields: termination_date, employee_role_code.
- Foreign Keys: home_office_id -> Office.
- Accepted Values or Controlled Domains: employment_status should be a controlled domain such as Active, Leave, Terminated, or comparable business status.
- Validation Rules:

| Rule | Enforcement |
| --- | --- |
| Employee number is required and cannot be null. | Hard Reject |
| Employee must reference a valid home office. | Hard Reject |
| Duplicate employee business keys are not allowed. | Hard Reject |
| A terminated employee should not be used as an active crew lead. | Warn and Flag |

- Update Behavior: Historical employee identity is preserved. Status changes are tracked as business events rather than by overwriting the original record.

## Project Contract

- Business Purpose: Represents the business project that work is performed under.
- Grain: One row per project.
- Business Key: Project code, supplied by the source system and immutable.
- Candidate Primary Key: Project identifier.
- Required Fields: project_code, project_name, project_status.
- Nullable Fields: project_description, parent_project_code.
- Foreign Keys: None.
- Accepted Values or Controlled Domains: project_status should use a controlled list, such as Planned, Active, Closed, or Cancelled.
- Validation Rules:

| Rule | Enforcement |
| --- | --- |
| Project code is required and cannot be null. | Hard Reject |
| Duplicate project business keys are not allowed. | Hard Reject |
| Project name should not be blank. | Warn and Flag |

- Update Behavior: Project definitions remain stable, and lifecycle changes are recorded without changing the original business key.

## Job Site Contract

- Business Purpose: Represents a physical job site that belongs to a project and is associated with a weather location.
- Grain: One row per job site.
- Business Key: Job site code, supplied by the source system and immutable.
- Candidate Primary Key: Job site identifier.
- Required Fields: job_site_code, job_site_name, project_id, weather_location_code.
- Nullable Fields: job_site_description.
- Foreign Keys: project_id -> Project.
- Accepted Values or Controlled Domains: weather_location_code must be one of the configured locations: TX-DAL, TX-HOU, or TX-AUS.
- Validation Rules:

| Rule | Enforcement |
| --- | --- |
| Job site code is required and cannot be null. | Hard Reject |
| Job site must reference a valid project. | Hard Reject |
| Duplicate job site business keys are not allowed. | Hard Reject |
| Weather location must be one of the three approved locations. | Hard Reject |

- Update Behavior: Job site identity is preserved. If location or project assignment changes, the historical record remains intact and lineage is maintained.

## Crew Contract

- Business Purpose: Represents a field crew that operates from a home office and may be led by an employee.
- Grain: One row per crew.
- Business Key: Crew code, supplied by the source system and immutable.
- Candidate Primary Key: Crew identifier.
- Required Fields: crew_code, home_office_id, crew_status.
- Nullable Fields: crew_lead_employee_id, crew_description.
- Foreign Keys: home_office_id -> Office; crew_lead_employee_id -> Employee.
- Accepted Values or Controlled Domains: crew_status should be a controlled business status such as Active, Inactive, or Disbanded.
- Validation Rules:

| Rule | Enforcement |
| --- | --- |
| Crew code is required and cannot be null. | Hard Reject |
| Crew must reference a valid home office. | Hard Reject |
| Duplicate crew business keys are not allowed. | Hard Reject |
| When populated, crew_lead_employee_id must reference an active Employee. | Hard Reject |
| The crew lead should normally belong to the same home office as the crew. | Warn and Flag |
| A missing crew lead is allowed temporarily but must be flagged. | Warn and Flag |

- Update Behavior: Crew identity remains stable. Changes to crew composition or leadership are tracked as business changes rather than by overwriting the initial record.

## Activity Contract

- Business Purpose: Represents the type of field activity being planned or executed.
- Grain: One row per activity.
- Business Key: Activity code, supplied by the source system and immutable.
- Candidate Primary Key: Activity identifier.
- Required Fields: activity_code, activity_name.
- Nullable Fields: activity_description, activity_category.
- Foreign Keys: None.
- Accepted Values or Controlled Domains: activity_code and activity_name should be controlled and business-readable.
- Validation Rules:

| Rule | Enforcement |
| --- | --- |
| Activity code is required and cannot be null. | Hard Reject |
| Duplicate activity business keys are not allowed. | Hard Reject |
| Activity name should not be blank. | Warn and Flag |

- Update Behavior: Activity definitions remain stable unless the business meaning changes materially.

## Field Schedule Contract

- Business Purpose: Represents the planned execution of work for a job site, project, and crew over a time window.
- Grain: One row per schedule occurrence.
- Business Key: The immutable source schedule identifier supplied by the source system.
- Candidate Primary Key: Schedule identifier.
- Required Fields: schedule_id, job_site_id, project_id, crew_id, scheduled_start_timestamp, scheduled_end_timestamp, scheduled_date, planned_crew_hours, planned_labor_hours, schedule_status.
- Nullable Fields: rescheduled_from_schedule_id, cancellation_reason_code, approved_adjustment_flag, approved_exception_note.
- Foreign Keys: job_site_id -> Job Site; project_id -> Project; crew_id -> Crew; rescheduled_from_schedule_id -> Field Schedule.
- Accepted Values or Controlled Domains: schedule_status must be one of Scheduled, In Progress, Completed, Delayed, Cancelled, or Rescheduled.
- Validation Rules:

| Rule | Enforcement |
| --- | --- |
| scheduled_end_timestamp must be greater than scheduled_start_timestamp. | Hard Reject |
| scheduled_date must equal the date portion of scheduled_start_timestamp. | Hard Reject |
| planned_crew_hours must equal the scheduled duration unless an approved adjustment field or documented exception exists. | Warn and Flag |
| planned_labor_hours must equal planned_crew_hours multiplied by the applicable crew size. | Hard Reject |
| project_id must match the Project associated with job_site_id. | Hard Reject |
| Completed schedules cannot be rescheduled. | Hard Reject |
| Rescheduled rows must have a valid successor row. | Hard Reject |
| Original timestamps cannot be edited after rescheduling. | Hard Reject |
| Reschedule lineage cannot self-reference or cycle. | Hard Reject |
| Status must be one of the controlled values. | Hard Reject |

- Update Behavior: Rescheduling is immutable. The original schedule row is never overwritten. The original row is marked as Rescheduled or Cancelled, and a new row is created with a new identifier and a rescheduled_from_schedule_id that preserves lineage.

## Equipment Type Contract

- Business Purpose: Represents the classification of equipment for planning, assignment, and safety rules.
- Grain: One row per equipment type.
- Business Key: Equipment type code, supplied by the source system and immutable.
- Candidate Primary Key: Equipment type identifier.
- Required Fields: equipment_type_code, equipment_type_name.
- Nullable Fields: equipment_type_description, equipment_category.
- Foreign Keys: None.
- Accepted Values or Controlled Domains: equipment_type_code and equipment_type_name should be controlled and business-readable.
- Validation Rules:

| Rule | Enforcement |
| --- | --- |
| Equipment type code is required and cannot be null. | Hard Reject |
| Duplicate equipment type business keys are not allowed. | Hard Reject |
| Equipment type name should not be blank. | Warn and Flag |

- Update Behavior: Equipment type definitions are stable and should not be altered in a way that changes historical meaning.

## Equipment Contract

- Business Purpose: Represents a physical asset that can be assigned to job sites and schedules.
- Grain: One row per equipment asset.
- Business Key: Equipment code, supplied by the source system and immutable.
- Candidate Primary Key: Equipment identifier.
- Required Fields: equipment_code, equipment_type_id, equipment_status.
- Nullable Fields: serial_number, asset_tag, equipment_description.
- Foreign Keys: equipment_type_id -> Equipment Type.
- Accepted Values or Controlled Domains: equipment_status should use a controlled domain such as Available, In Use, Out of Service, or Retired.
- Validation Rules:

| Rule | Enforcement |
| --- | --- |
| Equipment code is required and cannot be null. | Hard Reject |
| Equipment must reference a valid equipment type. | Hard Reject |
| Duplicate equipment business keys are not allowed. | Hard Reject |
| Status should be populated with a controlled value. | Warn and Flag |

- Update Behavior: Equipment identity remains stable; operational status changes are tracked without changing the original business key.

## Equipment Assignment Contract

- Business Purpose: Represents the assignment of equipment to a project and job site over a defined time window.
- Grain: One row per equipment assignment period.
- Business Key: The immutable assignment identifier supplied by the source system.
- Candidate Primary Key: Assignment identifier.
- Required Fields: assignment_id, equipment_id, job_site_id, project_id, assignment_start_timestamp.
- Nullable Fields: assignment_end_timestamp, assignment_note.
- Foreign Keys: equipment_id -> Equipment; job_site_id -> Job Site; project_id -> Project.
- Accepted Values or Controlled Domains: assignment timestamps must be valid business timestamps.
- Validation Rules:

| Rule | Enforcement |
| --- | --- |
| assignment_end_timestamp must be greater than assignment_start_timestamp when populated. | Hard Reject |
| project_id must match the Project associated with job_site_id. | Hard Reject |
| The same equipment cannot have overlapping assignment periods. | Hard Reject |
| Adjacent assignment boundaries are valid. | Informational |

- Update Behavior: Assignment records preserve the historical record of equipment usage. A new assignment row is created for a new period rather than overwriting the prior period.

## Safety Threshold Contract

- Business Purpose: Defines the business rules that determine when a field activity is above or below an acceptable threshold for a metric or weather condition.
- Grain: One row per active or historical safety threshold rule.
- Business Key: The immutable threshold identifier supplied by the source system.
- Candidate Primary Key: Threshold identifier.
- Required Fields: threshold_id, activity_id, metric_code, comparison_operator, unit, threshold_value_or_code_set, severity, recommended_action_code, effective_start_date, is_active, override_flag.
- Nullable Fields: equipment_type_id, effective_end_date, threshold_value, weather_code_set.
- Foreign Keys: activity_id -> Activity; equipment_type_id -> Equipment Type when populated.
- Accepted Values or Controlled Domains: comparison_operator must be compatible with the threshold structure; weather rules use weather_code_set rather than numeric min/max values; numeric rules use compatible units and valid numeric bounds; critical override rules set override_flag = true.
- Validation Rules:

| Rule | Enforcement |
| --- | --- |
| effective_end_date must be null or on or after effective_start_date. | Hard Reject |
| Active effective periods cannot overlap for the same activity, metric, severity, and optional equipment type. | Hard Reject |
| comparison_operator must be compatible with the threshold structure. | Hard Reject |
| Weather code rules must use weather_code_set rather than numeric min/max values. | Hard Reject |
| Numeric rules must use compatible units and valid numeric bounds. | Hard Reject |
| recommended_action_code is required. | Hard Reject |
| Critical override rules must set override_flag = true. | Hard Reject |
| Ambiguous or conflicting active safety rules are not allowed. | Hard Reject |

- Update Behavior: Thresholds preserve historical validity periods. New rules are added without deleting prior active versions, and inactive versions remain visible for traceability.

## Cross-Entity Validation Rules

| Rule | Enforcement |
| --- | --- |
| Foreign keys must resolve to existing records in the referenced entities. | Hard Reject |
| Field Schedule project_id must be consistent with the project associated with its job_site_id. | Hard Reject |
| Equipment Assignment project_id must be consistent with the project associated with its job_site_id. | Hard Reject |
| Reschedule lineage must preserve a valid chain and must not self-reference or cycle. | Hard Reject |
| Equipment assignment overlap for the same equipment is not allowed. | Hard Reject |
| Safety threshold effective periods must not overlap for the same activity, metric, severity, and optional equipment type. | Hard Reject |
| Weather location must be restricted to TX-DAL, TX-HOU, or TX-AUS. | Hard Reject |
| Cross-office crew assignment is allowed only as a warning condition. | Warn and Flag |
| Duplicate business keys across records of the same entity are not allowed. | Hard Reject |
| Missing or ambiguous business values that are required by the source contract must not be silently corrected. | Hard Reject |

## Silver Validation Responsibilities

Silver validation is responsible for accepting, rejecting, and flagging records according to these contracts.

- Accepted records must satisfy all Hard Reject rules and have no unresolved Warn and Flag issues.
- Rejected records must be excluded from downstream use until corrected or otherwise approved by the business owner.
- Warning flags must be preserved as validation outcomes so that downstream consumers can distinguish between clean, questionable, and rejected data.
- Validation reason codes should be attached to each outcome so that the reason for acceptance, rejection, or warning is traceable.
- Lineage metadata must be preserved for rescheduled and historical records so the current record can be traced to its predecessor and successor rows.
- Bronze source values must be preserved for traceability; Silver must not overwrite or fabricate missing business values.
- Silver may standardize or normalize values only when the normalization is clearly defined and does not change the source business meaning.

## Deferred Version 2 Rules

The following rules are intentionally deferred to a later phase because they are not required for Version 1 source contracts:

- Direct weather requests for each job site.
- Forecast accuracy measurement using observed weather.
- More advanced employee-role eligibility rules beyond the initial crew-lead rule.
- Explicit equipment transit or handoff states.
- Multi-crew schedules or shared equipment allocation if the business model requires those patterns later.

This document governs Phase 10 synthetic data generation and Silver validation for the approved operational source model.