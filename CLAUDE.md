# CLAUDE.md - AI Assistant Guide for Patient Allocation Optimization Project

## Project Overview

This repository implements and compares **optimization methods for the Patient Allocation in Hospitals problem**. It's an academic project demonstrating how hybrid approaches (metaheuristics + exact methods) can achieve optimal or near-optimal solutions efficiently.

**Problem Domain**: Bi-objective hospital patient allocation
- **Objective 1 (f₁)**: Minimize operational costs (admission delays, OR overtime/undertime)
- **Objective 2 (f₂)**: Balance workload across wards and time periods

**Solution Approaches**:
1. **Exact Methods**: MILP with Gurobi or CBC (Branch & Bound)
2. **Metaheuristics**: Simulated Annealing, Tabu Search, ILS, VNS
3. **Hybrid Methods**: Metaheuristics provide warm start for exact solvers

## Repository Structure

```
artificial-intelligence/
├── README.md                      # Comprehensive project documentation (Portuguese)
├── QUICK_START.md                 # Quick start guide (Portuguese)
├── CLAUDE.md                      # This file - AI assistant guide
│
├── Core Modules:
│   ├── data_parser.py             # Parses .dat files into Python objects
│   ├── milp_model.py              # Gurobi-based MILP solver (Method 1)
│   ├── CBC_milp.py                # CBC-based MILP solver (open-source alternative)
│   ├── metaheuristics.py          # SA, Tabu, ILS, VNS implementations
│   └── hybrid_solver.py           # Hybrid approach: metaheuristics + MILP
│
├── Analysis & Benchmarking:
│   ├── pareto_generator.py        # Generates Pareto frontiers for bi-objective
│   ├── Pareto_front_generator.py  # Alternative Pareto generation script
│   ├── Pareto_curve_2.py          # Pareto curve visualization
│   └── box_benchmark.py           # Benchmark with boxplot visualizations
│
├── Data:
│   ├── uploads/                   # Input .dat files (s0m0.dat, s0m1.dat, etc.)
│   ├── flexible_large.dat         # Large test instance
│   └── flexible_xlarge.dat        # Extra-large test instance
│
└── Output:
    ├── output/                    # General output plots
    ├── output_boxplot/            # Boxplot benchmark results
    └── output_dotplot/            # Dot plot benchmark results
```

## Key Concepts & Domain Knowledge

### Problem Components

**PatientAllocationData** (data_parser.py):
- **Patients**: Each has specialization, admission window [earliest, latest], length of stay (LOS), surgery duration, daily workload
- **Wards**: Bed capacity, workload capacity, major specialization, minor specializations (up to M)
- **Specialisms**: Workload factors, operating theater (OT) time availability per day
- **Carryover**: Pre-existing patients/workload from previous planning periods

### Decision Variables

- **y[p,w,d]**: Binary - patient p assigned to ward w on day d
- **x[w,d]**: Continuous - normalized workload in ward w on day d
- **z**: Continuous - maximum workload across all wards/days
- **v[s,d]**, **u[s,d]**: Continuous - overtime/undertime for specialization s on day d

### Constraints

1. Each patient admitted exactly once
2. Bed capacity not exceeded (includes carryover patients)
3. OT time availability respected (with overtime/undertime variables)
4. Patient-ward compatibility (specialization matching)
5. Admission within time window [earliest, latest]

### Objective Function

```
minimize λ₁·f₁ + λ₂·f₂

where:
  f₁ = operational cost (overtime + undertime + delays)
  f₂ = workload balance (minimize maximum normalized workload)
  λ₁, λ₂ ∈ [0,1] are user-defined weights
```

## Development Workflows

### 1. Working with Data Files

**.dat File Format**:
- Plain text, tab-separated values
- Sections: Seed, M, Weights, Days, Specialisms, Wards, Patients
- Located in `uploads/` directory

**Loading Data**:
```python
from data_parser import PatientAllocationData

data = PatientAllocationData('uploads/s0m0.dat')
data.print_summary()  # Display parsed data
```

### 2. Running Optimization Methods

**Method 1: Pure MILP (Gurobi)**:
```python
from milp_model import PatientAllocationMILP

model = PatientAllocationMILP(data, lambda1=0.5, lambda2=0.5)
model.build_model()
results = model.solve(time_limit=300, threads=4)
model.print_solution()
```

**Method 2: Pure MILP (CBC - Open Source)**:
```python
from CBC_milp import PatientAllocationMILP_CBC

model = PatientAllocationMILP_CBC(data, lambda1=0.5, lambda2=0.5)
model.build_model()
results = model.solve(time_limit=300)
```

**Method 3: Metaheuristics Only**:
```python
from metaheuristics import run_metaheuristics

# Run ILS or VNS
results = run_metaheuristics(
    data,
    lambda1=0.5,
    lambda2=0.5,
    method='ILS',  # or 'VNS'
    max_time_min=5,
    max_iter=100
)
```

**Method 4: Hybrid Approach**:
```python
from hybrid_solver import HybridSolverCBC

solver = HybridSolverCBC(data, lambda1=0.5, lambda2=0.5)
results = solver.solve(
    metaheuristic='ILS',
    mh_max_iter=50,
    mh_max_time_min=5,
    milp_time_limit=300,
    use_warm_start=True
)
```

### 3. Generating Pareto Frontiers

For bi-objective analysis, vary λ₁ and λ₂:

```bash
python pareto_generator.py -d uploads/s0m0.dat --num_points 11
```

This creates multiple solutions exploring the trade-off between operational cost and workload balance.

### 4. Benchmarking

```bash
python box_benchmark.py -d uploads/*.dat --runs 10
```

Runs multiple algorithms with different random seeds and generates statistical comparisons.

## Coding Conventions

### Python Style

- **Language**: Python 3.7+
- **Docstrings**: Triple-quoted strings with Args/Returns sections
- **Comments**: Portuguese in original code, but English acceptable for new code
- **Naming**:
  - Classes: `PascalCase` (e.g., `PatientAllocationData`)
  - Functions/methods: `snake_case` (e.g., `greedy_feasible_by_window_strict`)
  - Variables: `snake_case`
  - Constants: `UPPER_CASE` (rare in this codebase)

### Common Patterns

**Solution Representation**:
```python
# Dictionary mapping patient_id to assignment
allocation = {
    'P1': {'ward': 'W1', 'day': 0},
    'P2': {'ward': 'W2', 'day': 1},
    ...
}
```

**Objective Calculation**:
```python
from metaheuristics import objective_value

obj = objective_value(data, allocation, lambda1, lambda2)
# Returns (total_obj, f1, f2)
```

**Feasibility Checking**:
```python
from metaheuristics import feasible_after_change_beds

is_feasible = feasible_after_change_beds(data, allocation)
# or with a proposed change:
is_feasible = feasible_after_change_beds(data, allocation,
                                         change=('P1', 'W2', 3))
```

## Dependencies

### Required Libraries

```bash
pip install gurobipy pulp matplotlib pandas seaborn numpy
```

**Core Dependencies**:
- **gurobipy**: Commercial MILP solver (free academic license available)
- **pulp**: Python Linear Programming library (interfaces with CBC)
- **matplotlib**: Plotting and visualization
- **pandas**: Data manipulation for benchmarking
- **seaborn**: Statistical visualizations
- **numpy**: Numerical operations

**Solver Requirements**:
- **Gurobi**: Requires license (free for academics at https://www.gurobi.com/)
- **CBC**: Open-source, automatically installed with PuLP

## Testing & Execution

### Quick Tests

**Test Data Parser**:
```bash
python data_parser.py
# Expected: Loads s0m0.dat and prints summary
```

**Test MILP Model**:
```bash
python milp_model.py
# Expected: Solves with Gurobi, shows optimal solution
```

**Test Metaheuristics**:
```bash
python metaheuristics.py
# Expected: Runs greedy + local search + ILS, shows results
```

**Test Hybrid**:
```bash
python hybrid_solver.py
# Expected: Runs metaheuristic then MILP with warm start
```

### Expected Results (s0m0.dat)

| Method | Time | Objective | Gap to Optimal |
|--------|------|-----------|----------------|
| Gurobi MILP | ~0.01s | ~5380.91 | 0% (optimal) |
| CBC MILP | ~varies | ~5380.91 | 0% (if converged) |
| ILS | ~0.2s | ~5600-5800 | +4-8% |
| VNS | ~0.2s | ~5600-5800 | +4-8% |
| Hybrid | ~0.2s | ~5380.91 | 0% (often optimal) |

*Note: Times and objectives vary by hardware and random seed*

## AI Assistant Guidelines

### When Making Changes

1. **Read Before Write**: Always read existing files before modifying
2. **Preserve Language**: Keep Portuguese comments/docstrings unless improving clarity
3. **Test Changes**: After modifications, suggest running the appropriate test
4. **Dependencies**: Check if new code requires additional libraries
5. **Data Compatibility**: Ensure changes work with existing .dat file format

### Common Tasks

**Adding a New Metaheuristic**:
1. Add implementation to `metaheuristics.py`
2. Follow pattern: greedy construction → local improvement → advanced search
3. Use `objective_value()` and `feasible_after_change_beds()` utilities
4. Return results dict with: `{'objective_value': ..., 'solve_time': ..., 'solution': ...}`

**Modifying Objective Function**:
1. Update in both `milp_model.py` (Gurobi) and `CBC_milp.py` (CBC)
2. Update in `metaheuristics.py` (function `objective_value()`)
3. Update in `hybrid_solver.py` if warm start logic depends on it
4. Test with multiple λ₁, λ₂ values

**Adding New Constraints**:
1. Modify MILP models first (`milp_model.py`, `CBC_milp.py`)
2. Update metaheuristic feasibility checks (`feasible_after_change_beds`, etc.)
3. Update greedy construction if it affects initial feasible solutions
4. Document the constraint's mathematical formulation

**Adding Visualization**:
1. Add to appropriate script (`pareto_generator.py`, `box_benchmark.py`, etc.)
2. Use matplotlib/seaborn for consistency
3. Save to appropriate output directory (`output/`, `output_boxplot/`, etc.)
4. Use descriptive filenames with timestamps if running multiple benchmarks

### Best Practices

**Performance Optimization**:
- Profile before optimizing (use `time.time()` for timing)
- For large instances, prefer CBC over Gurobi if license issues
- Metaheuristics are fast (~seconds) vs MILP (~minutes to hours)
- Warm starting MILP with metaheuristic solution typically saves 30-70% time

**Code Quality**:
- Add type hints for new functions: `def func(data: PatientAllocationData) -> dict:`
- Include docstrings with Args/Returns sections
- Handle edge cases: empty patient list, zero capacity, etc.
- Use meaningful variable names (avoid `a`, `b`, `x` except for MILP variables)

**Error Handling**:
- Check file existence before parsing
- Validate data consistency (e.g., earliest <= latest for patients)
- Handle solver failures gracefully (MILP may timeout on large instances)
- Provide informative error messages

**Git Workflow**:
- Work on branch: `claude/claude-md-mi66braawkvwl7ax-01QK7kWR5TmKCBhD2TcCBCyK`
- Commit messages in English or Portuguese (be consistent)
- Don't commit large output files (.png, .pdf) unless essential
- Update README.md if adding major features

### Debugging Tips

**MILP Not Solving**:
- Check constraint feasibility (overconstrained?)
- Increase time_limit
- Try CBC instead of Gurobi (or vice versa)
- Check data file for inconsistencies

**Metaheuristic Poor Results**:
- Increase iterations (`max_iter`)
- Increase time budget (`max_time_min`)
- Check greedy construction is producing feasible solutions
- Verify objective function calculation matches MILP

**Memory Issues on Large Instances**:
- Reduce number of MILP variables (tighten time windows)
- Use metaheuristics only (skip MILP)
- Process data in batches
- Increase system swap space

### Useful Commands

**Check Python Environment**:
```bash
python --version  # Should be 3.7+
pip list | grep -E 'gurobipy|pulp|matplotlib'
```

**Quick Data File Inspection**:
```bash
head -30 uploads/s0m0.dat  # See first lines
grep "Patients:" uploads/s0m0.dat  # Count patients
```

**Monitor Long-Running Processes**:
```bash
python hybrid_solver.py 2>&1 | tee log.txt  # Log output
```

## Key Files Reference

| File | Lines | Purpose | When to Modify |
|------|-------|---------|----------------|
| `data_parser.py` | ~204 | Parse .dat files | Adding new data fields |
| `milp_model.py` | ~363 | Gurobi MILP solver | Changing constraints/objectives |
| `CBC_milp.py` | ~600+ | CBC MILP solver | Same as milp_model.py |
| `metaheuristics.py` | ~1200+ | Heuristic algorithms | Adding new metaheuristics |
| `hybrid_solver.py` | ~600+ | Hybrid approach | Tuning warm start logic |
| `pareto_generator.py` | ~700+ | Pareto frontier | Bi-objective analysis |
| `box_benchmark.py` | ~700+ | Statistical benchmarking | Evaluation methodology |

## Project Context

**Academic Course**: Artificial Intelligence
**Topic**: Metaheuristics for Optimization/Decision Problems
**Theme**: Patient Allocation in Hospitals
**Key Reference**: Pieter Smet (2023), "Generating balanced workload allocations in hospitals", Operations Research for Health Care, Vol. 38

**Primary Goals**:
1. Demonstrate metaheuristics can find good solutions quickly
2. Show exact methods guarantee optimality but may be slow
3. Prove hybrid approaches combine best of both worlds
4. Enable bi-objective analysis via Pareto frontiers

**Success Metrics**:
- Solution quality (objective value, gap to optimal)
- Computational time (seconds to minutes)
- Feasibility (all constraints satisfied)
- Scalability (performance on large instances)

## Additional Resources

- **Dataset Source**: https://data.mendeley.com/datasets/3mv4rtxtfs/1
- **Paper**: https://www.sciencedirect.com/science/article/pii/S2211692323000139
- **Gurobi Docs**: https://www.gurobi.com/documentation/
- **PuLP Docs**: https://coin-or.github.io/pulp/

---

**Last Updated**: 2025-11-19
**Repository**: https://github.com/byjoaofilipe/artificial-intelligence
**Branch**: `claude/claude-md-mi66braawkvwl7ax-01QK7kWR5TmKCBhD2TcCBCyK`

---

## Quick Reference Card

```python
# Load data
from data_parser import PatientAllocationData
data = PatientAllocationData('uploads/s0m0.dat')

# Solve with MILP
from milp_model import PatientAllocationMILP
model = PatientAllocationMILP(data, lambda1=0.5, lambda2=0.5)
model.build_model()
results = model.solve(time_limit=300)

# Solve with metaheuristics
from metaheuristics import run_metaheuristics
results = run_metaheuristics(data, lambda1=0.5, lambda2=0.5, method='ILS')

# Solve with hybrid
from hybrid_solver import HybridSolverCBC
solver = HybridSolverCBC(data, lambda1=0.5, lambda2=0.5)
results = solver.solve(metaheuristic='ILS', milp_time_limit=300)

# Generate Pareto frontier
# See pareto_generator.py for detailed usage
```

**Remember**: This is research/academic code. Prioritize correctness and clarity over premature optimization.
