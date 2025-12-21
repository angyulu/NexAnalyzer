# UI Layout Specification

## ADDED Requirements

### Requirement: Three-Panel Desktop Layout

The application SHALL display a single-page layout with three horizontal panels on desktop viewports (≥1024px width).

#### Scenario: Desktop layout proportions
- **WHEN** the viewport width is ≥1024px
- **THEN** the page displays three columns with proportions: 20% (left) / 50% (center) / 30% (right)

#### Scenario: Panel content assignment
- **WHEN** the three-panel layout is rendered
- **THEN** the left panel contains the file list with status badges
- **AND** the center panel contains the unified spectrum plot
- **AND** the right panel contains all processing controls in accordion sections

### Requirement: Stacked Mobile Layout

The application SHALL display a stacked vertical layout on mobile viewports (<1024px width).

#### Scenario: Mobile layout stacking order
- **WHEN** the viewport width is <1024px
- **THEN** the page displays vertically stacked sections in order: file list (top) → control panel (middle) → plot (bottom)

#### Scenario: Mobile functionality preservation
- **WHEN** using the mobile stacked layout
- **THEN** all features from the desktop layout remain accessible and functional

### Requirement: Single-Page Workflow

The application SHALL present all workflow stages (pre-process, fit, export) on a single page without tabs.

#### Scenario: No tab navigation
- **WHEN** the application loads
- **THEN** no tab navigation UI (st.tabs) is visible
- **AND** all workflow stages are accessible via accordion sections in the right panel

#### Scenario: Workflow continuity
- **WHEN** a user completes a processing step
- **THEN** the page does not navigate away or reload
- **AND** the next workflow section automatically expands
