# metaheuristics.py - VERSION WITHOUT EXTERNAL LOCAL SEARCH

"""
Fast metaheuristics for Patient Allocation.

PIPELINE:
- Greedy constructive heuristic producing a bed-feasible solution
- ILS with internal fast local search and bed-capacity penalties
- VNS with internal fast local search and bed-capacity penalties

KEY DESIGN CHOICES:
- No external greedy_local_improvement (it was too slow)
- ILS/VNS internal local search samples only a subset of patients and few days
- Timeouts enforced on local search and metaheuristics
"""

import random
import math
import time
import copy
from collections import defaultdict
from data_parser import PatientAllocationData


# =====================================================================
#                            UTILITIES
# =====================================================================

def compatible_wards_for_patient(data: PatientAllocationData, patient):
    """
    Return the list of wards compatible with a given patient.

    Compatibility is based on specialization:
    - patient's specialization equals ward["major_specialization"], or
    - patient's specialization is in ward["minor_specializations"].
    """
    spec = patient["specialization"]
    wards = []
    for wname, ward in data.wards.items():
        if spec == ward["major_specialization"] or spec in ward["minor_specializations"]:
            wards.append(wname)
    return wards


def count_beds_used_on_day(data: PatientAllocationData, allocation, ward_name, d):
    """
    Count how many beds are used in ward 'ward_name' on day d.

    Includes:
    - carryover patients fixed in data
    - all allocated patients whose length of stay covers day d.
    """
    used = data.wards[ward_name]["carryover_patients"][d]
    for pid, a in allocation.items():
        if a["ward"] != ward_name:
            continue
        p = data.patients[pid]
        if a["day"] <= d < a["day"] + p["los"]:
            used += 1
    return used


def feasible_after_change_beds(data: PatientAllocationData, allocation, change=None):
    """
    Check bed-capacity feasibility, optionally after a single change.

    Parameters
    ----------
    allocation : dict
        Current allocation {pid: {"ward": w, "day": d}}.
    change : tuple or None
        If None, the whole 'allocation' is checked as is.
        If (pid, new_ward, new_day), a shallow copy with this modification
        is checked instead.

    Returns
    -------
    bool
        True if for all wards and days bed usage does not exceed capacity.
    """
    if change is not None:
        pid, new_ward, new_day = change
        allocation = allocation.copy()
        allocation[pid] = {"ward": new_ward, "day": new_day}

    for wname, ward in data.wards.items():
        cap = ward["bed_capacity"]
        for d in range(data.num_days):
            used = count_beds_used_on_day(data, allocation, wname, d)
            if used > cap:
                return False
    return True


def bed_capacity_violations(data: PatientAllocationData, allocation):
    """
    Compute the total amount of bed-capacity violations.

    Returns
    -------
    int
        Sum over all wards and days of (used beds - capacity), whenever positive.
        This is used as a soft penalty measure in the metaheuristics.
    """
    vio = 0
    for wname, ward in data.wards.items():
        cap = ward["bed_capacity"]
        for d in range(data.num_days):
            used = count_beds_used_on_day(data, allocation, wname, d)
            if used > cap:
                vio += (used - cap)
    return vio


def compute_ot_used_by_spec_day(data: PatientAllocationData, allocation, spec, d):
    """
    Compute operating theatre time used by specialization 'spec' on day d.

    Sums the surgery_duration of all patients whose:
    - specialization == spec
    - surgery day == d.
    """
    total = 0
    for pid, a in allocation.items():
        p = data.patients[pid]
        if p["specialization"] == spec and a["day"] == d:
            total += p["surgery_duration"]
    return total


def compute_workload_normalized_and_z(data: PatientAllocationData, allocation):
    """
    Compute normalized workloads and their maximum.

    For each ward/day:
    - accumulate workload from carryover and allocated patients
    - apply workload_factor when specialization is minor in that ward
    - normalize by workload_capacity
    - track the maximum normalized workload z (for balancing)

    Returns
    -------
    x : dict
        Mapping (ward_name, day) -> normalized workload.
    z : float
        Maximum normalized workload across all ward/day pairs.
    """
    x = {}
    z = 0.0
    for wname, ward in data.wards.items():
        cap = ward["workload_capacity"]
        for d in range(data.num_days):
            total_w = ward["carryover_workload"][d]
            for pid, a in allocation.items():
                if a["ward"] != wname:
                    continue
                p = data.patients[pid]
                admit = a["day"]
                if admit <= d < admit + p["los"]:
                    day_of_stay = d - admit
                    if 0 <= day_of_stay < len(p["workload_per_day"]):
                        base = p["workload_per_day"][day_of_stay]
                        spec = p["specialization"]
                        if spec != ward["major_specialization"] and spec in ward["minor_specializations"]:
                            base *= data.specialisms[spec]["workload_factor"]
                        total_w += base
            x[(wname, d)] = total_w / cap if cap > 0 else 0.0
            z = max(z, x[(wname, d)])
    return x, z


def compute_objective_components(data: PatientAllocationData, allocation):
    """
    Compute the individual objective components.

    Returns
    -------
    delays : float
        Sum over patients of (admission day - earliest) if positive.
    total_overtime : float
        Total OR overtime across all specializations/days.
    total_undertime : float
        Total OR unused time across all specializations/days.
    z : float
        Maximum normalized workload across ward/day pairs.
    x_map : dict
        Normalized workload map (ward, day) -> x.
    ot_used_map : dict
        Detailed OR usage map: (spec, day) -> (used, available, overtime, undertime).
    """
    # Admission delays
    delays = 0.0
    for pid, a in allocation.items():
        p = data.patients[pid]
        delays += max(0, a["day"] - p["earliest"])

    # OR overtime / undertime
    total_overtime = 0.0
    total_undertime = 0.0
    ot_used_map = {}
    for spec in data.specialisms.keys():
        for d in range(data.num_days):
            used = compute_ot_used_by_spec_day(data, allocation, spec, d)
            avail = data.specialisms[spec]["ot_time"][d]
            if used > avail:
                total_overtime += (used - avail)
                ot_used_map[(spec, d)] = (used, avail, used - avail, 0)
            else:
                total_undertime += (avail - used)
                ot_used_map[(spec, d)] = (used, avail, 0, avail - used)

    x_map, z = compute_workload_normalized_and_z(data, allocation)
    return delays, total_overtime, total_undertime, z, x_map, ot_used_map


def objective_value(data: PatientAllocationData, allocation, lambda1=0.5, lambda2=0.5):
    """
    Compute the scalarized objective:
        f = λ1 * f1 + λ2 * f2

    where:
        f1 = weight_overtime * OT_overtime
           + weight_undertime * OT_undertime
           + weight_delay * delays
        f2 = z (maximum normalized workload)

    Parameters
    ----------
    lambda1, lambda2 : float
        Weights for the scalarization of the multi-objective problem.
    """
    delays, ovt, undt, z, _, _ = compute_objective_components(data, allocation)
    f1 = data.weight_overtime * ovt + data.weight_undertime * undt + data.weight_delay * delays
    f2 = z
    return lambda1 * f1 + lambda2 * f2


def objective_value_penalized(
    data: PatientAllocationData,
    allocation,
    lambda1=0.5,
    lambda2=0.5,
    penalty_weight=1000.0
):
    """
    Penalized objective used inside metaheuristics.

    f_pen = f + penalty_weight * (total bed-capacity violations)

    This allows the search to temporarily explore infeasible regions while
    strongly favoring solutions with fewer or no violations.
    """
    f_obj = objective_value(data, allocation, lambda1, lambda2)
    violations = bed_capacity_violations(data, allocation)
    return f_obj + penalty_weight * violations


# =====================================================================
#                      GREEDY CONSTRUCTIVE HEURISTIC
# =====================================================================

def _score_trial(data, alloc, pid, w, d, lambda1, lambda2):
    """
    Evaluate a trial assignment used only as a fallback in greedy.

    Computes the objective value if we assign patient pid to ward w on day d,
    assuming bed-capacity feasibility. If that move would violate bed capacity,
    returns +infinity.
    """
    trial = copy.deepcopy(alloc)
    trial[pid] = {"ward": w, "day": d}
    if not feasible_after_change_beds(data, alloc, (pid, w, d)):
        return float("inf")
    return objective_value(data, trial, lambda1, lambda2)


def _tiny_repair_shift_same_ward_day_forward(
    data,
    alloc,
    ward_name,
    congested_day,
    max_shifts=3
):
    """
    Small local repair to free beds on a congested day in a ward.

    Strategy:
    - Identify patients currently occupying beds in 'ward_name' on 'congested_day'.
    - Try to move up to 'max_shifts' of them one day forward within their time window.
    - Only accept moves that maintain bed feasibility.

    Returns
    -------
    bool
        True if at least one patient was shifted, False otherwise.
    """
    candidates = []
    for pid, a in alloc.items():
        if a["ward"] != ward_name:
            continue
        p = data.patients[pid]
        if a["day"] <= congested_day < a["day"] + p["los"]:
            candidates.append(pid)

    random.shuffle(candidates)
    tried = 0
    for pid in candidates:
        if tried >= max_shifts:
            break
        p = data.patients[pid]
        a_day = alloc[pid]["day"]
        if a_day + 1 <= min(p["latest"], data.num_days - 1):
            trial = copy.deepcopy(alloc)
            trial[pid]["day"] = a_day + 1
            if feasible_after_change_beds(data, trial):
                alloc[pid]["day"] = a_day + 1
                return True
        tried += 1
    return False


def greedy_feasible_by_window_strict(data: PatientAllocationData):
    """
    Construct a bed-feasible solution using a strict greedy heuristic.

    Procedure
    ---------
    1. Sort patients by:
       - (latest - earliest) ascending (tighter windows first)
       - earliest ascending
       - length of stay descending
    2. For each patient:
       - greedily try compatible wards/days respecting bed capacities
       - if no direct placement is found, attempt a small repair to free beds
       - if still no placement, select the ward/day combination minimizing
         the objective among feasible options
    3. If a patient cannot be placed at all, raise a RuntimeError
       (instance is too saturated).

    Returns
    -------
    alloc : dict
        Feasible allocation mapping each pid to {"ward": w, "day": d}.
    """
    patients_order = sorted(
        data.patients.items(),
        key=lambda kv: (
            (kv[1]["latest"] - kv[1]["earliest"]),
            kv[1]["earliest"],
            -kv[1]["los"]
        )
    )

    alloc = {}

    for pid, p in patients_order:
        wards = compatible_wards_for_patient(data, p)
        los = p["los"]
        placed = False

        # 1) Pure greedy respecting bed capacity
        for w in wards:
            ward = data.wards[w]
            cap = ward["bed_capacity"]

            for d in range(p["earliest"], min(p["latest"] + 1, data.num_days)):
                ok = True
                for day_check in range(d, min(d + los, data.num_days)):
                    used = count_beds_used_on_day(data, alloc, w, day_check)
                    if used >= cap:
                        ok = False
                        break
                if ok:
                    alloc[pid] = {"ward": w, "day": d}
                    placed = True
                    break
            if placed:
                break

        # 2) Small repair if we did not manage to place the patient
        if not placed:
            for w in wards:
                for d in range(p["earliest"], min(p["latest"] + 1, data.num_days)):
                    for day_check in range(d, min(d + los, data.num_days)):
                        used = count_beds_used_on_day(data, alloc, w, day_check)
                        cap = data.wards[w]["bed_capacity"]
                        if used >= cap:
                            if _tiny_repair_shift_same_ward_day_forward(
                                data, alloc, w, day_check, max_shifts=3
                            ):
                                break

            # Try again greedily after repair
            for w in wards:
                cap = data.wards[w]["bed_capacity"]
                for d in range(p["earliest"], min(p["latest"] + 1, data.num_days)):
                    ok = True
                    for day_check in range(d, min(d + los, data.num_days)):
                        used = count_beds_used_on_day(data, alloc, w, day_check)
                        if used >= cap:
                            ok = False
                            break
                    if ok:
                        alloc[pid] = {"ward": w, "day": d}
                        placed = True
                        break
                if placed:
                    break

        # 3) Fallback: choose the best feasible position by objective value
        if not placed:
            lambda1, lambda2 = 0.5, 0.5
            best_score = float('inf')
            best_w, best_d = None, None

            for w in wards:
                for d in range(p["earliest"], min(p["latest"] + 1, data.num_days)):
                    score = _score_trial(data, alloc, pid, w, d, lambda1, lambda2)
                    if score < best_score:
                        best_score = score
                        best_w, best_d = w, d

            if best_w is not None:
                alloc[pid] = {"ward": best_w, "day": best_d}
                placed = True

        if not placed:
            raise RuntimeError(f"❌ No bed available for {pid} — instance too saturated.")

    return alloc


# =====================================================================
#                   ITERATED LOCAL SEARCH (ILS) - FAST
# =====================================================================

class IteratedLocalSearch:
    """
    Fast Iterated Local Search (ILS) for Patient Allocation.

    Characteristics:
    - Internal fast local search:
        * samples only a subset of patients
        * tests a few random days per patient
        * uses penalized objective
    - Uses bed-feasible best solution tracking
    - Perturbation mechanism triggered by stagnation
    """

    def __init__(
        self,
        data: PatientAllocationData,
        lambda1=0.5,
        lambda2=0.5,
        penalty_weight=1000.0
    ):
        self.data = data
        self.lambda1 = lambda1
        self.lambda2 = lambda2
        self.penalty_weight = penalty_weight

        self.best_feasible_allocation = None
        self.best_feasible_value = float("inf")
        self.solve_time = None

        # Stagnation and perturbation parameters
        self.STAGNATION_LIMIT = 20
        self.PERTURB_BASE_RATIO = 0.10
        self.PERTURB_MAX_RATIO = 0.25

    def _perturbation_mixed(self, allocation, intensity=0.10):
        """
        Mixed perturbation operator.

        Selects up to 'intensity * |patients|' patients to perturb:
        - half are the worst contributors with regard to admission delay
        - half are randomly selected

        For each selected patient:
        - assign a random compatible ward
        - assign a random day within [earliest, latest]
        """
        perturbed = copy.deepcopy(allocation)
        num_to_perturb = max(1, int(len(self.data.patients) * intensity))

        # Identify worst contributors (by delay)
        worst_pids = []
        for pid in self.data.patients.keys():
            p = self.data.patients[pid]
            a = allocation[pid]
            delay_score = max(0, a["day"] - p["earliest"])
            worst_pids.append((delay_score, pid))
        worst_pids.sort(reverse=True)
        worst_contributors = [pid for _, pid in worst_pids[:num_to_perturb // 2]]

        # 50% random + 50% worst contributors
        num_random = num_to_perturb // 2
        patients_random = random.sample(list(self.data.patients.keys()), num_random)
        patients_to_perturb = patients_random + worst_contributors

        for pid in patients_to_perturb:
            p = self.data.patients[pid]
            wards = compatible_wards_for_patient(self.data, p)
            new_ward = random.choice(wards)
            new_day = random.randint(p["earliest"], min(p["latest"], self.data.num_days - 1))
            perturbed[pid] = {"ward": new_ward, "day": new_day}

        return perturbed

    def _local_search_fast(self, allocation, max_time_seconds=30):
        """
        Fast local search used inside ILS.

        Features:
        - works directly on the passed allocation (no global deepcopy)
        - samples only a subset of patients per iteration (~30%)
        - tests a few random days (up to 3) per patient
        - uses the penalized objective to guide the search
        - stops on:
            * no improvement,
            * max_iterations reached, or
            * time limit exceeded
        """
        t0 = time.time()
        current = allocation
        curr_val = objective_value_penalized(
            self.data, current, self.lambda1, self.lambda2, self.penalty_weight
        )

        iterations = 0
        max_iterations = 10
        num_patients_to_check = max(10, int(len(self.data.patients) * 0.3))

        while iterations < max_iterations:
            if time.time() - t0 > max_time_seconds:
                break

            improved = False
            iterations += 1

            pids_sample = random.sample(
                list(self.data.patients.keys()),
                min(num_patients_to_check, len(self.data.patients))
            )

            for pid in pids_sample:
                if time.time() - t0 > max_time_seconds:
                    break

                p = self.data.patients[pid]
                base = current[pid]

                possible_days = list(range(p["earliest"], min(p["latest"] + 1, self.data.num_days)))
                days_to_try = random.sample(possible_days, min(3, len(possible_days)))

                for d in days_to_try:
                    if d == base["day"]:
                        continue

                    old_day = current[pid]["day"]
                    current[pid]["day"] = d
                    val = objective_value_penalized(
                        self.data, current, self.lambda1, self.lambda2, self.penalty_weight
                    )

                    if val + 1e-9 < curr_val:
                        curr_val = val
                        improved = True
                        break  # first-improvement strategy
                    else:
                        current[pid]["day"] = old_day

                if improved:
                    break

            if not improved:
                break

        return current, curr_val

    def solve(
        self,
        start_allocation,
        max_iterations=50,
        max_time_minutes=10,
        verbose=True
    ):
        """
        Run the full ILS procedure starting from a feasible allocation.

        Steps
        -----
        1. Validate starting solution (must be bed-feasible).
        2. Initialize best_feasible with the starting objective.
        3. Iterations:
            - run fast local search on the current solution
            - if the resulting solution is bed-feasible, evaluate the
              non-penalized objective and update the global best if improved
            - count iterations without improvement; when stagnation exceeds
              STAGNATION_LIMIT, apply a perturbation around the current best
        4. Stop when:
            - time limit is reached, OR
            - max_iterations is reached, OR
            - extended stagnation triggers early stopping.

        Returns
        -------
        dict
            {
                "objective_value": best feasible objective,
                "solve_time": runtime in seconds,
                "allocation": best feasible allocation
            }
        """
        t0 = time.time()
        max_time_seconds = max_time_minutes * 60

        current = copy.deepcopy(start_allocation)

        # Ensure starting solution is bed-feasible
        if feasible_after_change_beds(self.data, current):
            self.best_feasible_allocation = copy.deepcopy(current)
            self.best_feasible_value = objective_value(
                self.data, current, self.lambda1, self.lambda2
            )
        else:
            raise ValueError("Start allocation must be feasible with respect to beds!")

        no_improve_counter = 0

        if verbose:
            print("\n" + "=" * 60)
            print("ITERATED LOCAL SEARCH (ILS) - FAST")
            print("=" * 60)
            print(f"Initial f = {self.best_feasible_value:.2f}")
            print(f"Max time: {max_time_minutes} minutes")

        for iteration in range(max_iterations):
            if time.time() - t0 > max_time_seconds:
                if verbose:
                    print(f"\n⏱️  Timeout reached ({max_time_minutes} min)")
                break

            # Local search from current solution (penalized objective)
            current, curr_val_pen = self._local_search_fast(current, max_time_seconds=30)

            # If locally improved solution is bed-feasible, evaluate clean objective
            if feasible_after_change_beds(self.data, current):
                curr_val = objective_value(self.data, current, self.lambda1, self.lambda2)

                if curr_val + 1e-9 < self.best_feasible_value:
                    self.best_feasible_value = curr_val
                    self.best_feasible_allocation = copy.deepcopy(current)
                    no_improve_counter = 0

                    if verbose:
                        elapsed = time.time() - t0
                        print(f"Iter {iteration} ({elapsed:.0f}s): f = {curr_val:.2f} ✓ NEW BEST")
                else:
                    no_improve_counter += 1
            else:
                no_improve_counter += 1

            # Apply perturbation when stagnation is detected
            if no_improve_counter >= self.STAGNATION_LIMIT:
                intensity = min(
                    self.PERTURB_MAX_RATIO,
                    self.PERTURB_BASE_RATIO * (1 + no_improve_counter / self.STAGNATION_LIMIT)
                )

                if verbose:
                    print(f"Iter {iteration}: Perturbation ({intensity * 100:.0f}% patients)")

                current = self._perturbation_mixed(self.best_feasible_allocation, intensity)
                no_improve_counter = 0

            # Extended stagnation → early stop
            if no_improve_counter >= self.STAGNATION_LIMIT * 2:
                if verbose:
                    print(f"\n⚠️  Stopping early: no improvement")
                break

        self.solve_time = time.time() - t0

        if verbose:
            print(f"\n✓ ILS done in {self.solve_time:.2f}s")
            print(f"Best feasible f: {self.best_feasible_value:.2f}")

        return {
            "objective_value": self.best_feasible_value,
            "solve_time": self.solve_time,
            "allocation": self.best_feasible_allocation
        }


# =====================================================================
#              VARIABLE NEIGHBORHOOD SEARCH (VNS) - FAST
# =====================================================================

class VariableNeighborhoodSearch:
    """
    Fast Variable Neighborhood Search (VNS) for Patient Allocation.

    Neighborhoods
    -------------
    N1: small day shift for a single patient
    N2: change ward for a single patient
    N3: multi-move (day or ward) for 1–2 patients
    N4: swap assignments (ward + day) between two compatible patients

    Workflow
    --------
    - Start from a bed-feasible solution
    - For k = 1..K_MAX:
        * shake (apply Nk)
        * run fast local search (penalized)
        * if a feasible and improved solution is found:
              - update global best
              - set current = improved solution
              - reset k = 1 (intensification)
          else:
              - k += 1 (diversification)
    """

    def __init__(
        self,
        data: PatientAllocationData,
        lambda1=0.5,
        lambda2=0.5,
        penalty_weight=1000.0
    ):
        self.data = data
        self.lambda1 = lambda1
        self.lambda2 = lambda2
        self.penalty_weight = penalty_weight

        self.best_feasible_allocation = None
        self.best_feasible_value = float("inf")
        self.solve_time = None

        self.K_MAX = 4

    # ------------------- Neighborhood definitions -------------------

    def _shake_N1(self, allocation):
        """
        Neighborhood N1: small day shift for a single patient.

        Randomly picks a patient and shifts their day by -2, -1, +1, or +2
        if the new day remains within [earliest, latest].
        """
        shaken = copy.deepcopy(allocation)
        pid = random.choice(list(self.data.patients.keys()))
        p = self.data.patients[pid]
        current_day = shaken[pid]["day"]
        shifts = [-2, -1, 1, 2]
        shift = random.choice(shifts)
        new_day = current_day + shift
        if p["earliest"] <= new_day <= min(p["latest"], self.data.num_days - 1):
            shaken[pid]["day"] = new_day
        return shaken

    def _shake_N2(self, allocation):
        """
        Neighborhood N2: ward change for a single patient.

        Randomly picks a patient and moves them to a different compatible ward
        (if more than one ward is available).
        """
        shaken = copy.deepcopy(allocation)
        pid = random.choice(list(self.data.patients.keys()))
        p = self.data.patients[pid]
        wards = compatible_wards_for_patient(self.data, p)
        if len(wards) > 1:
            new_ward = random.choice([w for w in wards if w != shaken[pid]["ward"]])
            shaken[pid]["ward"] = new_ward
        return shaken

    def _shake_N3(self, allocation):
        """
        Neighborhood N3: multi-move for 1–2 patients.

        For each selected patient:
        - either change day randomly within [earliest, latest], OR
        - change ward randomly among compatible wards.
        """
        shaken = copy.deepcopy(allocation)
        pids_to_move = random.sample(
            list(self.data.patients.keys()),
            min(2, len(self.data.patients))
        )
        for pid in pids_to_move:
            p = self.data.patients[pid]
            if random.random() < 0.5:
                new_day = random.randint(p["earliest"], min(p["latest"], self.data.num_days - 1))
                shaken[pid]["day"] = new_day
            else:
                wards = compatible_wards_for_patient(self.data, p)
                if len(wards) > 1:
                    new_ward = random.choice(wards)
                    shaken[pid]["ward"] = new_ward
        return shaken

    def _shake_N4(self, allocation):
        """
        Neighborhood N4: swap assignments between two patients.

        Swaps ward and day between two randomly selected patients, if:
        - each new ward is compatible with the other patient
        - each new day is within the other's admissible window.
        """
        shaken = copy.deepcopy(allocation)
        if len(self.data.patients) >= 2:
            pids = random.sample(list(self.data.patients.keys()), 2)
            p1_id, p2_id = pids
            p1 = self.data.patients[p1_id]
            p2 = self.data.patients[p2_id]
            a1 = shaken[p1_id]
            a2 = shaken[p2_id]
            p1_wards = compatible_wards_for_patient(self.data, p1)
            p2_wards = compatible_wards_for_patient(self.data, p2)
            if (
                a2["ward"] in p1_wards and
                a1["ward"] in p2_wards and
                p1["earliest"] <= a2["day"] <= min(p1["latest"], self.data.num_days - 1) and
                p2["earliest"] <= a1["day"] <= min(p2["latest"], self.data.num_days - 1)
            ):
                shaken[p1_id] = {"ward": a2["ward"], "day": a2["day"]}
                shaken[p2_id] = {"ward": a1["ward"], "day": a1["day"]}
        return shaken

    def _shake(self, allocation, k):
        """
        Dispatch method for shaking according to neighborhood index k.
        """
        if k == 1:
            return self._shake_N1(allocation)
        elif k == 2:
            return self._shake_N2(allocation)
        elif k == 3:
            return self._shake_N3(allocation)
        else:
            return self._shake_N4(allocation)

    # ------------------- Internal local search -------------------

    def _local_search_fast(self, allocation, max_time_seconds=15):
        """
        Fast internal local search used inside VNS.

        Similar to the ILS local search but:
        - fewer iterations
        - smaller patient sample
        - fewer days tested per patient
        """
        t0 = time.time()
        current = allocation
        curr_val = objective_value_penalized(
            self.data, current, self.lambda1, self.lambda2, self.penalty_weight
        )

        iterations = 0
        max_iterations = 5
        num_patients_to_check = max(10, int(len(self.data.patients) * 0.2))

        while iterations < max_iterations:
            if time.time() - t0 > max_time_seconds:
                break

            improved = False
            iterations += 1

            pids_sample = random.sample(
                list(self.data.patients.keys()),
                min(num_patients_to_check, len(self.data.patients))
            )

            for pid in pids_sample:
                if time.time() - t0 > max_time_seconds:
                    break

                p = self.data.patients[pid]
                base = current[pid]

                possible_days = list(range(p["earliest"], min(p["latest"] + 1, self.data.num_days)))
                days_to_try = random.sample(possible_days, min(2, len(possible_days)))

                for d in days_to_try:
                    if d == base["day"]:
                        continue

                    old_day = current[pid]["day"]
                    current[pid]["day"] = d
                    val = objective_value_penalized(
                        self.data, current, self.lambda1, self.lambda2, self.penalty_weight
                    )

                    if val + 1e-9 < curr_val:
                        curr_val = val
                        improved = True
                        break
                    else:
                        current[pid]["day"] = old_day

                if improved:
                    break

            if not improved:
                break

        return current, curr_val

    def solve(
        self,
        start_allocation,
        max_iterations=100,
        max_time_minutes=10,
        verbose=True
    ):
        """
        Run the Variable Neighborhood Search (VNS) starting from a feasible solution.

        Steps
        -----
        1. Validate starting solution (must be bed-feasible).
        2. Initialize best_feasible with starting objective.
        3. Main loop:
            - For k in {1..K_MAX}:
                * shake current solution in Nk
                * run fast local search from shaken solution
                * if the resulting solution is bed-feasible and better:
                    - update global best
                    - set current = improved solution
                    - reset k = 1
                  else:
                    - k += 1
        4. Stop when:
            - time limit is reached, OR
            - max_iterations is reached.

        Returns
        -------
        dict
            {
                "objective_value": best feasible objective,
                "solve_time": runtime in seconds,
                "allocation": best feasible allocation
            }
        """
        t0 = time.time()
        max_time_seconds = max_time_minutes * 60

        current = copy.deepcopy(start_allocation)

        if feasible_after_change_beds(self.data, current):
            self.best_feasible_allocation = copy.deepcopy(current)
            self.best_feasible_value = objective_value(
                self.data, current, self.lambda1, self.lambda2
            )
        else:
            raise ValueError("Start allocation must be feasible with respect to beds!")

        if verbose:
            print("\n" + "=" * 60)
            print("VARIABLE NEIGHBORHOOD SEARCH (VNS) - FAST")
            print("=" * 60)
            print(f"Initial f = {self.best_feasible_value:.2f}")
            print(f"Max time: {max_time_minutes} minutes")

        k = 1
        iteration = 0

        while iteration < max_iterations:
            if time.time() - t0 > max_time_seconds:
                if verbose:
                    print(f"\n⏱️  Timeout reached ({max_time_minutes} min)")
                break

            iteration += 1

            # Shake current solution in neighborhood Nk
            shaken = self._shake(current, k)
            improved_solution, improved_val_pen = self._local_search_fast(
                shaken, max_time_seconds=15
            )

            if feasible_after_change_beds(self.data, improved_solution):
                improved_val = objective_value(
                    self.data, improved_solution, self.lambda1, self.lambda2
                )

                if improved_val + 1e-9 < self.best_feasible_value:
                    self.best_feasible_value = improved_val
                    self.best_feasible_allocation = copy.deepcopy(improved_solution)
                    current = improved_solution
                    k = 1  # restart from smallest neighborhood

                    if verbose:
                        elapsed = time.time() - t0
                        print(
                            f"Iter {iteration} ({elapsed:.0f}s): "
                            f"f = {improved_val:.2f} ✓ NEW BEST (N{k})"
                        )
                else:
                    k += 1
            else:
                k += 1

            if k > self.K_MAX:
                k = 1

            if iteration % 20 == 0 and verbose:
                elapsed = time.time() - t0
                print(
                    f"Iter {iteration} ({elapsed:.0f}s): "
                    f"exploring N{k}, best = {self.best_feasible_value:.2f}"
                )

        self.solve_time = time.time() - t0

        if verbose:
            print(f"\n✓ VNS done in {self.solve_time:.2f}s")
            print(f"Best feasible f: {self.best_feasible_value:.2f}")

        return {
            "objective_value": self.best_feasible_value,
            "solve_time": self.solve_time,
            "allocation": self.best_feasible_allocation
        }


# =====================================================================
#                               RUNNER
# =====================================================================

def run_metaheuristics(
    data: PatientAllocationData,
    lambda1=0.5,
    lambda2=0.5,
    ils_penalty=1000.0,
    ils_max_iter=50,
    ils_max_time_min=5,
    vns_penalty=1000.0,
    vns_max_iter=100,
    vns_max_time_min=5,
    verbose=True
):
    """
    Run the full metaheuristic pipeline on a given instance:

        1. Greedy constructive heuristic
        2. Iterated Local Search (ILS) starting from the greedy solution
        3. Variable Neighborhood Search (VNS) starting from the greedy solution
           (can optionally be started from ILS result as a variant)

    Returns
    -------
    dict
        {
            "greedy_det": {"f", "t", "allocation"},
            "ils": {...},
            "vns": {...},
            "total_time": total runtime in seconds
        }
    """
    t_all = time.time()

    if verbose:
        print("\n" + "=" * 78)
        print("PIPELINE: Greedy -> ILS (FAST) -> VNS (FAST)")
        print("=" * 78)

    # 1) Greedy constructive
    t0 = time.time()
    alloc0 = greedy_feasible_by_window_strict(data)
    t_construct = time.time() - t0
    f0 = objective_value(data, alloc0, lambda1, lambda2)
    if verbose:
        print(f"\nGreedy feasible: f={f0:.2f}  (t={t_construct:.2f}s)")

    # 2) ILS starting from greedy solution
    ILS = IteratedLocalSearch(data, lambda1, lambda2, penalty_weight=ils_penalty)
    ils_res = ILS.solve(
        alloc0,
        max_iterations=ils_max_iter,
        max_time_minutes=ils_max_time_min,
        verbose=verbose
    )

    # 3) VNS starting from greedy solution
    # (optionally could use ils_res["allocation"] instead of alloc0)
    VNS = VariableNeighborhoodSearch(data, lambda1, lambda2, penalty_weight=vns_penalty)
    vns_res = VNS.solve(
        alloc0,
        max_iterations=vns_max_iter,
        max_time_minutes=vns_max_time_min,
        verbose=verbose
    )

    total_time = time.time() - t_all

    if verbose:
        print("\n" + "-" * 78)
        print("SUMMARY")
        print("-" * 78)
        print(f"Greedy  : f={f0:.2f}, t={t_construct:.2f}s")
        print(f"ILS     : f={ils_res['objective_value']:.2f}, t={ils_res['solve_time']:.2f}s")
        print(f"VNS     : f={vns_res['objective_value']:.2f}, t={vns_res['solve_time']:.2f}s")
        print(f"TOTAL   : {total_time:.2f}s")
        print("-" * 78)

    return {
        "greedy_det": {"f": f0, "t": t_construct, "allocation": alloc0},
        "ils": ils_res,
        "vns": vns_res,
        "total_time": total_time
    }


if __name__ == "__main__":
    # Example standalone run on a specific .dat file.
    # Adjust 'data_path' to match your local environment if needed.
    data_path = "/Users/paolopascarelli/Desktop/Introduction to AI/flexible_large.dat"
    data = PatientAllocationData(data_path)

    run_metaheuristics(
        data,
        lambda1=0.5,
        lambda2=0.5,
        ils_penalty=1000.0,
        ils_max_iter=50,
        ils_max_time_min=5,
        vns_penalty=1000.0,
        vns_max_iter=100,
        vns_max_time_min=5,
        verbose=True
    )
