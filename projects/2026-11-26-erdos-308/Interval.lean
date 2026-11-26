import Std

namespace OpenMath308

/--
If 1 through r are attainable and every attainable value is at most r + 2,
the attainable positive integers are an initial interval, provided that any
attainable positive value has an attainable neighbour. Egyptian fractions
have this property by toggling the denominator 1.
-/
theorem interval_of_neighbours (attainable : Nat → Prop) (r : Nat)
    (initial : ∀ k, 0 < k → k ≤ r → attainable k)
    (upper : ∀ k, attainable k → k ≤ r + 2)
    (neighbours : ∀ k, 0 < k → attainable k → attainable (k - 1) ∨ attainable (k + 1)) :
    ∃ m, ∀ k, (0 < k ∧ attainable k) ↔ (0 < k ∧ k ≤ m) := by
  classical
  by_cases top : attainable (r + 2)
  · have prev : attainable (r + 1) := by
      rcases neighbours (r + 2) (by omega) top with h | h
      · exact h
      · have := upper _ h
        omega
    refine ⟨r + 2, ?_⟩
    intro k
    constructor
    · exact fun ⟨pos, hk⟩ => ⟨pos, upper _ hk⟩
    · rintro ⟨pos, bound⟩
      refine ⟨pos, ?_⟩
      by_cases small : k ≤ r
      · exact initial _ pos small
      · have : k = r + 1 ∨ k = r + 2 := by omega
        rcases this with h | h
        · exact h ▸ prev
        · exact h ▸ top
  · by_cases nextValue : attainable (r + 1)
    · refine ⟨r + 1, ?_⟩
      intro k
      constructor
      · rintro ⟨pos, hk⟩
        have bound := upper _ hk
        have ne : k ≠ r + 2 := fun h => top (h ▸ hk)
        exact ⟨pos, by omega⟩
      · rintro ⟨pos, bound⟩
        by_cases small : k ≤ r
        · exact ⟨pos, initial _ pos small⟩
        · have h : k = r + 1 := by omega
          exact ⟨pos, h ▸ nextValue⟩
    · refine ⟨r, ?_⟩
      intro k
      constructor
      · rintro ⟨pos, hk⟩
        have bound := upper _ hk
        have ne₁ : k ≠ r + 1 := fun h => nextValue (h ▸ hk)
        have ne₂ : k ≠ r + 2 := fun h => top (h ▸ hk)
        exact ⟨pos, by omega⟩
      · exact fun ⟨pos, bound⟩ => ⟨pos, initial _ pos bound⟩

end OpenMath308

namespace OpenMath308

/-- 'tail k' means k is represented using denominators from 2 through N.
For each such sum, denominator 1 may be either omitted or included. -/
def withOne (tail : Nat → Prop) (k : Nat) : Prop :=
  tail k ∨ ∃ j, tail j ∧ k = j + 1

theorem withOne_neighbours (tail : Nat → Prop) (k : Nat) (_ : 0 < k)
    (hk : withOne tail k) :
    withOne tail (k - 1) ∨ withOne tail (k + 1) := by
  rcases hk with h | ⟨j, hj, rfl⟩
  · exact Or.inr (Or.inr ⟨k, h, rfl⟩)
  · exact Or.inl (Or.inl hj)

/-- Certificate criterion specialized to optional use of denominator 1. -/
theorem interval_with_one (tail : Nat → Prop) (r : Nat)
    (initial : ∀ k, 0 < k → k ≤ r → withOne tail k)
    (upper : ∀ k, withOne tail k → k ≤ r + 2) :
    ∃ m, ∀ k, (0 < k ∧ withOne tail k) ↔ (0 < k ∧ k ≤ m) :=
  interval_of_neighbours _ r initial upper (withOne_neighbours tail)

end OpenMath308
