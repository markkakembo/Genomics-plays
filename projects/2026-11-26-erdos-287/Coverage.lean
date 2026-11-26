import Std

namespace Erdos287Certificate

/-- Each new witness covers all integers from the current start through p.
The empty tail succeeds once the right endpoint has been passed. -/
def covers (num den start stop : Nat) : List Nat → Bool
  | [] => decide (stop < start)
  | p :: ps => decide (start ≤ p ∧ den * p ≤ num * start) &&
      covers num den (p + 1) stop ps

/-- Integer interval arithmetic only. The separate certificate verifier
establishes primality for each listed p and its partner (p+1)/2. -/
theorem covers_sound (num den stop : Nat) (ps : List Nat) (start : Nat)
    (checked : covers num den start stop ps = true) (n : Nat)
    (lo : start ≤ n) (hi : n ≤ stop) :
    ∃ p ∈ ps, n ≤ p ∧ den * p ≤ num * n := by
  induction ps generalizing start with
  | nil =>
    simp [covers] at checked
    omega
  | cons p ps ih =>
    simp only [covers, Bool.and_eq_true, decide_eq_true_eq] at checked
    by_cases hp : n ≤ p
    · exact ⟨p, List.mem_cons_self, hp,
        Nat.le_trans checked.1.2 (Nat.mul_le_mul_left num lo)⟩
    · obtain ⟨q, hq, left, right⟩ := ih (p + 1) checked.2 (by omega)
      exact ⟨q, List.mem_cons_of_mem _ hq, left, right⟩

end Erdos287Certificate
