export const springs = {
  snap: { type: "spring" as const, stiffness: 520, damping: 34 },
  smooth: { type: "spring" as const, stiffness: 260, damping: 30 },
  soft: { type: "spring" as const, stiffness: 160, damping: 26 },
};

export const stagger = 0.05;
