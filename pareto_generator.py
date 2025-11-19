"""
Benchmark Script with Dot Plots for Patient Allocation Algorithms

This script runs multiple iterations of 6 different algorithms on datasets and generates
dot plots for objective values across runs.

Usage:
    python benchmark_dotplot.py -d dataset1.dat dataset2.dat --runs 10
    python benchmark_dotplot.py -d data/*.dat --runs 5 --lambda1 0.5 --lambda2 0.5
"""

import argparse
import sys
import os
import time
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import pandas as pd
import seaborn as sns

# Import the algorithm modules
from data_parser import PatientAllocationData
from CBC_milp import PatientAllocationMILP_CBC
from metaheuristics import run_metaheuristics, run_metaheuristics_no_opt
from Hybrid_solver import HybridSolverCBC


class BenchmarkDotPlot:
    """
    Run multiple iterations of all algorithms and generate dot plots.
    """
    
    def __init__(self, datasets, num_runs=10, lambda1=0.5, lambda2=0.5, output_dir="output_dotplot"):
        """
        Initialize the benchmark runner.
        
        Args:
            datasets: List of paths to .dat files
            num_runs: Number of runs per algorithm per dataset
            lambda1: Initial weight for objective 1 (will vary per run)
            lambda2: Initial weight for objective 2 (will vary per run)
            output_dir: Directory to save output plots
        """
        self.datasets = datasets
        self.num_runs = num_runs
        self.initial_lambda1 = lambda1
        self.initial_lambda2 = lambda2
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Results storage: list of dictionaries for each run
        self.all_results = []
        
    def run_all(self, 
                milp_time_limit=300,
                mh_time=3,
                hybrid_mh_time=3,
                hybrid_milp_time=180,
                threads=4):
        """
        Run all algorithms multiple times on all datasets.
        
        Args:
            milp_time_limit: Time limit for pure MILP (seconds)
            mh_time: Time for metaheuristics (minutes)
            hybrid_mh_time: Time for metaheuristic phase in hybrid (minutes)
            hybrid_milp_time: Time for MILP phase in hybrid (seconds)
            threads: Number of threads for solvers
        """
        print("\n" + "=" * 80)
        print("BENCHMARK WITH DOT PLOTS - MULTIPLE RUNS")
        print("=" * 80)
        print(f"Datasets: {len(self.datasets)}")
        print(f"Runs per dataset: {self.num_runs}")
        print(f"Algorithms: MILP-CBC, MH-ILS, MH-VNS, MH-NoOpt-ILS, MH-NoOpt-VNS, Hybrid")
        print(f"Lambda weights: λ1 starts at 1.0 (decrement 0.1), λ2 starts at 0.0 (increment 0.1)")
        print("=" * 80)
        
        for dataset_idx, dataset_path in enumerate(self.datasets):
            dataset_name = Path(dataset_path).stem
            print(f"\n{'=' * 80}")
            print(f"DATASET {dataset_idx+1}/{len(self.datasets)}: {dataset_name}")
            print(f"{'=' * 80}")
            
            try:
                print(f"\n📂 Loading data from '{dataset_path}'...")
                data = PatientAllocationData(dataset_path)
                print(f"✓ Loaded: {len(data.patients)} patients, {len(data.wards)} wards, {data.num_days} days")
                
                # Now run metaheuristics and hybrid multiple times
                for run_idx in range(self.num_runs):
                    # Calculate lambda values for this run
                    # λ1 starts at 1.0 and decrements by 0.1 each run
                    # λ2 starts at 0.0 and increments by 0.1 each run
                    lambda1 = 1.0 - (run_idx * 0.1)
                    lambda2 = 0.0 + (run_idx * 0.1)
                    
                    # Ensure lambdas stay within valid range [0, 1]
                    lambda1 = max(0.0, min(1.0, lambda1))
                    lambda2 = max(0.0, min(1.0, lambda2))
                    
                    print(f"\n{'─' * 80}")
                    print(f"RUN {run_idx+1}/{self.num_runs} for {dataset_name}")
                    print(f"λ1 = {lambda1:.1f}, λ2 = {lambda2:.1f}")
                    print(f"{'─' * 80}")
                    
                    # Run MILP for this specific lambda combination
                    print(f"\nRunning MILP-CBC with λ1={lambda1:.1f}, λ2={lambda2:.1f}...")
                    milp_run_result = self._run_milp_cbc(data, milp_time_limit, threads, lambda1, lambda2)
                    
                    # Run Metaheuristics (with optimization)
                    print("Running Metaheuristics (ILS + VNS with optimization)...")
                    mh_result = run_metaheuristics(data, lambda1, lambda2)
                    
                    # Run Metaheuristics NO-OPT
                    print("Running Metaheuristics NO-OPT (ILS + VNS without optimization)...")
                    mh_no_opt_result = run_metaheuristics_no_opt(data, lambda1, lambda2)
                    
                    # Run Hybrid
                    print("Running Hybrid solver...")
                    hybrid_result = self._run_hybrid(data, hybrid_mh_time, hybrid_milp_time, threads, lambda1, lambda2)
                    
                    # Store results for this run
                    self._store_run_results(
                        dataset_name, 
                        run_idx,
                        lambda1,
                        lambda2,
                        milp_run_result['objective'],
                        milp_run_result['time'],
                        mh_result, 
                        mh_no_opt_result, 
                        hybrid_result
                    )
                    
                    print(f"✓ Run {run_idx+1} completed")
                
            except Exception as e:
                print(f"\n❌ ERROR processing dataset '{dataset_name}': {e}")
                import traceback
                traceback.print_exc()
        
        # Generate dot plots
        print(f"\n{'=' * 80}")
        print("GENERATING DOT PLOTS")
        print(f"{'=' * 80}")
        self._generate_dotplots()
        
        # Print summary statistics
        self._print_summary_statistics()
    
    def _run_milp_cbc(self, data, time_limit, threads, lambda1, lambda2):
        """Run pure MILP solver with CBC."""
        try:
            model = PatientAllocationMILP_CBC(data, lambda1, lambda2)
            model.build_model()
            
            start_time = time.time()
            results = model.solve(time_limit=time_limit, threads=threads, verbose=False)
            elapsed = time.time() - start_time
            
            if results:
                return {
                    'objective': results['objective_value'],
                    'time': elapsed,
                    'status': results['status']
                }
            else:
                return {
                    'objective': None,
                    'time': elapsed,
                    'status': 'NO_SOLUTION'
                }
        except Exception as e:
            print(f"❌ MILP failed: {e}")
            return {
                'objective': None,
                'time': None,
                'status': 'ERROR'
            }
    
    def _run_hybrid(self, data, mh_time, milp_time, threads, lambda1, lambda2):
        """Run hybrid solver."""
        try:
            hybrid = HybridSolverCBC(data, lambda1, lambda2)
            results = hybrid.solve(
                metaheuristic='ILS',
                mh_max_iter=50,
                mh_max_time_min=mh_time,
                milp_time_limit=milp_time,
                threads=threads,
                use_warm_start=True,
                verbose=False
            )
            return results
        except Exception as e:
            print(f"❌ Hybrid failed: {e}")
            return {
                'best_objective': None,
                'total_time': None,
                'best_method': 'ERROR'
            }
    
    def _store_run_results(self, dataset_name, run_idx, lambda1, lambda2, milp_optimal, milp_time,
                          mh_result, mh_no_opt_result, hybrid_result):
        """Store results from one run."""
        
        # Helper function to calculate optimality gap
        def calc_gap(algorithm_obj, optimal):
            if algorithm_obj is None or optimal is None or optimal == 0:
                return None
            # Gap = 1 - (optimal / algorithm_value)
            # If algorithm is worse (higher), gap is positive
            # If algorithm equals optimal, gap is 0
            gap = 1.0 - (optimal / algorithm_obj)
            return gap * 100  # Convert to percentage
        
        # Extract values
        mh_ils_obj = mh_result['ils']['objective_value']
        mh_ils_time = mh_result['ils']['solve_time']
        
        mh_vns_obj = mh_result['vns']['objective_value']
        mh_vns_time = mh_result['vns']['solve_time']
        
        mh_no_opt_ils_obj = mh_no_opt_result['ils']['objective_value']
        mh_no_opt_ils_time = mh_no_opt_result['ils']['solve_time']
        
        mh_no_opt_vns_obj = mh_no_opt_result['vns']['objective_value']
        mh_no_opt_vns_time = mh_no_opt_result['vns']['solve_time']
        
        hybrid_obj = hybrid_result['best_objective']
        hybrid_time = hybrid_result['total_time']
        
        # Store each algorithm result separately
        algorithms_data = [
            {
                'dataset': dataset_name,
                'run': run_idx,
                'lambda1': lambda1,
                'lambda2': lambda2,
                'algorithm': 'MILP-CBC',
                'time': milp_time,
                'objective': milp_optimal,
                'gap': 0.0  # MILP is the reference, gap is 0
            },
            {
                'dataset': dataset_name,
                'run': run_idx,
                'lambda1': lambda1,
                'lambda2': lambda2,
                'algorithm': 'MH-ILS',
                'time': mh_ils_time,
                'objective': mh_ils_obj,
                'gap': calc_gap(mh_ils_obj, milp_optimal)
            },
            {
                'dataset': dataset_name,
                'run': run_idx,
                'lambda1': lambda1,
                'lambda2': lambda2,
                'algorithm': 'MH-VNS',
                'time': mh_vns_time,
                'objective': mh_vns_obj,
                'gap': calc_gap(mh_vns_obj, milp_optimal)
            },
            {
                'dataset': dataset_name,
                'run': run_idx,
                'lambda1': lambda1,
                'lambda2': lambda2,
                'algorithm': 'MH-NoOpt-ILS',
                'time': mh_no_opt_ils_time,
                'objective': mh_no_opt_ils_obj,
                'gap': calc_gap(mh_no_opt_ils_obj, milp_optimal)
            },
            {
                'dataset': dataset_name,
                'run': run_idx,
                'lambda1': lambda1,
                'lambda2': lambda2,
                'algorithm': 'MH-NoOpt-VNS',
                'time': mh_no_opt_vns_time,
                'objective': mh_no_opt_vns_obj,
                'gap': calc_gap(mh_no_opt_vns_obj, milp_optimal)
            },
            {
                'dataset': dataset_name,
                'run': run_idx,
                'lambda1': lambda1,
                'lambda2': lambda2,
                'algorithm': 'Hybrid',
                'time': hybrid_time,
                'objective': hybrid_obj,
                'gap': calc_gap(hybrid_obj, milp_optimal)
            }
        ]
        
        self.all_results.extend(algorithms_data)
    
    def _generate_dotplots(self):
        """Generate dot plots for objective values - one plot per algorithm."""
        if not self.all_results:
            print("⚠️ No results to plot")
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(self.all_results)
        
        # Remove rows with None values in objective
        df_obj = df[df['objective'].notna()].copy()
        
        if df_obj.empty:
            print("⚠️ No valid objective data to plot")
            return
        
        # Set style
        sns.set_style("whitegrid")
        
        # Generate one plot per algorithm
        algorithms = ['MILP-CBC', 'MH-ILS', 'MH-VNS', 'MH-NoOpt-ILS', 'MH-NoOpt-VNS', 'Hybrid']
        
        for algo in algorithms:
            df_algo = df_obj[df_obj['algorithm'] == algo]
            if not df_algo.empty:
                self._plot_algorithm_dots(df_algo, algo)
        
        print(f"\n✓ Dot plots saved to '{self.output_dir}' directory")
    
    def _plot_algorithm_dots(self, df_algo, algorithm_name):
        """Plot dots for a single algorithm showing all runs."""
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Define colors for each algorithm
        algo_colors = {
            'MILP-CBC': '#2E86AB',
            'MH-ILS': '#792BAE',
            'MH-VNS': '#A23B72',
            'MH-NoOpt-ILS': '#8FA23B',
            'MH-NoOpt-VNS': '#C9184A',
            'Hybrid': '#F18F01'
        }
        
        color = algo_colors.get(algorithm_name, '#333333')
        
        # Get unique datasets
        datasets = sorted(df_algo['dataset'].unique())
        
        # If multiple datasets, group by dataset
        if len(datasets) > 1:
            # Plot dots for each dataset
            for i, dataset in enumerate(datasets):
                df_dataset = df_algo[df_algo['dataset'] == dataset]
                
                # X positions are run numbers, Y is objective value
                runs = df_dataset['run'].values
                objectives = df_dataset['objective'].values
                
                # Add slight jitter to avoid overlapping points
                x_jitter = runs + np.random.normal(0, 0.1, len(runs))
                
                ax.scatter(x_jitter, objectives,
                          color=color,
                          alpha=0.7,
                          s=100,
                          edgecolors='black',
                          linewidth=0.5,
                          label=dataset)
                
                # Connect dots with a line for each dataset
                sorted_indices = np.argsort(runs)
                ax.plot(runs[sorted_indices], objectives[sorted_indices],
                       color=color, alpha=0.3, linewidth=1.5, linestyle='--')
            
            # Add mean line across all runs
            mean_val = df_algo['objective'].mean()
            ax.axhline(y=mean_val, color='red', linestyle='-', 
                      linewidth=2, alpha=0.7, label=f'Overall Mean: {mean_val:.2f}')
            
            ax.legend(title='Dataset', loc='best', framealpha=0.9)
            
        else:
            # Single dataset - simpler plot
            dataset = datasets[0]
            runs = df_algo['run'].values
            objectives = df_algo['objective'].values
            
            # Sort by run number
            sorted_indices = np.argsort(runs)
            runs_sorted = runs[sorted_indices]
            objectives_sorted = objectives[sorted_indices]
            
            # Plot dots
            ax.scatter(runs_sorted, objectives_sorted,
                      color=color,
                      alpha=0.7,
                      s=150,
                      edgecolors='black',
                      linewidth=1,
                      zorder=3)
            
            # Connect with line
            ax.plot(runs_sorted, objectives_sorted,
                   color=color, alpha=0.4, linewidth=2, linestyle='-', zorder=2)
            
            # Add mean line
            mean_val = df_algo['objective'].mean()
            std_val = df_algo['objective'].std()
            ax.axhline(y=mean_val, color='red', linestyle='--', 
                      linewidth=2, alpha=0.7, label=f'Mean: {mean_val:.2f} (±{std_val:.2f})')
            
            # Add min/max lines
            min_val = df_algo['objective'].min()
            max_val = df_algo['objective'].max()
            ax.axhline(y=min_val, color='green', linestyle=':', 
                      linewidth=1.5, alpha=0.5, label=f'Best: {min_val:.2f}')
            ax.axhline(y=max_val, color='orange', linestyle=':', 
                      linewidth=1.5, alpha=0.5, label=f'Worst: {max_val:.2f}')
            
            ax.legend(loc='best', framealpha=0.9)
        
        # Statistics text box
        stats_text = f"Runs: {len(df_algo)}\n"
        stats_text += f"Mean: {df_algo['objective'].mean():.2f}\n"
        stats_text += f"Std: {df_algo['objective'].std():.2f}\n"
        stats_text += f"Min: {df_algo['objective'].min():.2f}\n"
        stats_text += f"Max: {df_algo['objective'].max():.2f}\n"
        stats_text += f"\nλ1: 1.0 → {df_algo['lambda1'].min():.1f}\n"
        stats_text += f"λ2: 0.0 → {df_algo['lambda2'].max():.1f}"
        
        ax.text(0.02, 0.98, stats_text,
               transform=ax.transAxes,
               fontsize=10,
               verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        ax.set_xlabel('Run Number', fontsize=12, fontweight='bold')
        ax.set_ylabel('Objective Value', fontsize=12, fontweight='bold')
        ax.set_title(f'{algorithm_name} - Objective Values Across All Runs\n(Lower is Better)', 
                     fontsize=14, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3)
        
        # Set x-axis to show integer run numbers
        if len(df_algo) > 0:
            max_run = df_algo['run'].max()
            ax.set_xticks(range(0, max_run + 1))
        
        plt.tight_layout()
        
        # Save with algorithm name in filename
        filename = f'{self.output_dir}/dotplot_{algorithm_name.replace("-", "_")}.png'
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"  ✓ Saved: {filename}")
        plt.close()
    
    def _print_summary_statistics(self):
        """Print summary statistics."""
        if not self.all_results:
            print("⚠️ No results to summarize")
            return
        
        df = pd.DataFrame(self.all_results)
        
        print(f"\n{'=' * 80}")
        print("SUMMARY STATISTICS")
        print(f"{'=' * 80}")
        
        print("\n📊 OBJECTIVE VALUE STATISTICS")
        print(f"{'─' * 80}")
        obj_stats = df.groupby('algorithm')['objective'].agg(['mean', 'median', 'std', 'min', 'max'])
        print(obj_stats.to_string())
        
        print("\n\n📊 EXECUTION TIME STATISTICS (seconds)")
        print(f"{'─' * 80}")
        time_stats = df.groupby('algorithm')['time'].agg(['mean', 'median', 'std', 'min', 'max'])
        print(time_stats.to_string())
        
        print(f"\n\n📊 OPTIMALITY GAP STATISTICS (%)")
        print(f"{'─' * 80}")
        df_no_milp = df[df['algorithm'] != 'MILP-CBC']
        if not df_no_milp.empty:
            gap_stats = df_no_milp.groupby('algorithm')['gap'].agg(['mean', 'median', 'std', 'min', 'max'])
            print(gap_stats.to_string())
        
        # Count how many times each algorithm achieved optimal (gap = 0)
        print(f"\n\n🎯 OPTIMAL SOLUTIONS ACHIEVED")
        print(f"{'─' * 80}")
        for algo in df_no_milp['algorithm'].unique():
            df_algo = df_no_milp[df_no_milp['algorithm'] == algo]
            optimal_count = (df_algo['gap'] == 0).sum()
            total_count = len(df_algo)
            percentage = (optimal_count / total_count * 100) if total_count > 0 else 0
            print(f"{algo:<20} {optimal_count}/{total_count} ({percentage:.1f}%)")
        
        # Best algorithm per dataset
        print(f"\n\n🏆 BEST ALGORITHM PER DATASET (by mean objective)")
        print(f"{'─' * 80}")
        for dataset in df['dataset'].unique():
            df_dataset = df[df['dataset'] == dataset]
            best_algo = df_dataset.groupby('algorithm')['objective'].mean().idxmin()
            best_obj = df_dataset.groupby('algorithm')['objective'].mean().min()
            print(f"{dataset:<30} {best_algo:<20} (obj={best_obj:.2f})")
        
        print(f"\n{'=' * 80}")


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Benchmark with dot plots for patient allocation algorithms",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run 10 iterations on multiple datasets
  python benchmark_dotplot.py -d data1.dat data2.dat --runs 10
  
  # Run on all .dat files in a directory
  python benchmark_dotplot.py -d data/*.dat --runs 5
  
  # Custom parameters
  python benchmark_dotplot.py -d data/*.dat --runs 10 --lambda1 0.6 --lambda2 0.4
        """
    )
    
    parser.add_argument(
        "-d", "--datasets",
        nargs="+",
        required=True,
        help="List of .dat files to process"
    )
    
    parser.add_argument(
        "--runs",
        type=int,
        default=10,
        help="Number of runs per algorithm per dataset. Default: 10"
    )
    
    parser.add_argument(
        "--lambda1",
        type=float,
        default=0.5,
        help="Weight for objective 1. Default: 0.5"
    )
    
    parser.add_argument(
        "--lambda2",
        type=float,
        default=0.5,
        help="Weight for objective 2. Default: 0.5"
    )
    
    parser.add_argument(
        "--milp-time",
        type=int,
        default=300,
        help="Time limit for MILP (seconds). Default: 300"
    )
    
    parser.add_argument(
        "--mh-time",
        type=int,
        default=3,
        help="Time for metaheuristics (minutes). Default: 3"
    )
    
    parser.add_argument(
        "--hybrid-mh-time",
        type=int,
        default=3,
        help="Time for metaheuristic phase in hybrid (minutes). Default: 3"
    )
    
    parser.add_argument(
        "--hybrid-milp-time",
        type=int,
        default=180,
        help="Time for MILP phase in hybrid (seconds). Default: 180"
    )
    
    parser.add_argument(
        "--threads",
        type=int,
        default=4,
        help="Number of threads for solvers. Default: 4"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="output_dotplot",
        help="Output directory for plots. Default: output_dotplot"
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Validate datasets exist
    valid_datasets = []
    for dataset in args.datasets:
        if os.path.exists(dataset):
            valid_datasets.append(dataset)
        else:
            print(f"⚠️ Warning: Dataset '{dataset}' not found, skipping...")
    
    if not valid_datasets:
        print("❌ ERROR: No valid datasets found!")
        sys.exit(1)
    
    print(f"\n✓ Found {len(valid_datasets)} valid dataset(s)")
    
    # Create benchmark runner
    runner = BenchmarkDotPlot(
        valid_datasets,
        num_runs=args.runs,
        lambda1=args.lambda1,
        lambda2=args.lambda2,
        output_dir=args.output
    )
    
    # Run all benchmarks
    try:
        runner.run_all(
            milp_time_limit=args.milp_time,
            mh_time=args.mh_time,
            hybrid_mh_time=args.hybrid_mh_time,
            hybrid_milp_time=args.hybrid_milp_time,
            threads=args.threads
        )
        
        print(f"\n✓ Benchmark completed successfully!")
        print(f"  Results saved to: {args.output}/")
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Execution interrupted by user (Ctrl+C)")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ ERROR during execution: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())