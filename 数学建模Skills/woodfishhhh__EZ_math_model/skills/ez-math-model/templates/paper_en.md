# {Title}

> Writing guidance: all placeholders, brace markers, prompts, bullets in body
> sections, and instructional text must be removed before `paper.md` is saved.
> Formal papers must not contain pipeline paths such as `runtime/`, `output/`,
> `summary.json`, `execution_log`, or manifest/debug text.

**Abstract**

Background paragraph (~100 words): describe the real-world setting, why this
problem matters, and which aspects this work addresses.

For Problem 1, we adopted {model name}. Specifically, {modeling idea}; using
{solution method} we obtained {core numerical result}. This indicates that
{brief takeaway}.

For Problem 2, we adopted {model name}. Specifically, {modeling idea}; using
{solution method} we obtained {core numerical result}. This indicates that
{brief takeaway}.

For Problem 3, we adopted {model name}. Specifically, {modeling idea}; using
{solution method} we obtained {core numerical result}. This indicates that
{brief takeaway}.

A sensitivity analysis on {key parameters} within a ±20% range showed
{sensitivity conclusion}, demonstrating that the proposed model is {robust /
stable} under reasonable parameter variations. Overall, the framework
established in this paper effectively {solves the problem}.

**Keywords**: {kw1}; {kw2}; {kw3}; {kw4}; {kw5}

---

# 1. Problem Restatement

## 1.1 Background

A single paragraph (~160 words) combining the original problem statement with
domain context, articulating why the problem matters and what this paper
addresses.

## 1.2 Problem Restatement

Based on the above context, this paper builds mathematical models to address
the following:

- Problem 1: {summary}
- Problem 2: {summary}
- Problem 3: {summary}

---

# 2. Problem Analysis

## 2.1 Analysis of Problem 1

Paragraph 1: This problem requires {goal} subject to {constraints}, and is
classified as a {model category} task (prediction / evaluation /
classification / optimization).

Paragraph 2: Given the data characteristics and modeling goals, {model name}
is initially adopted as the baseline. Compared to {alternative models}, its
advantage lies in {comparison}. The validation strategy is {validation plan}.

## 2.2 Analysis of Problem 2

(Same structure, ~250 words each.)

## 2.N Analysis of Problem N

---

# 3. Model Assumptions

(1) Assumption 1: {content}.
Justification: {domain-specific argument}.

(2) Assumption 2: {content}.
Justification: {...}.

(3) Assumption 3: {content}.
Justification: {...}.

(4) Assumption 4: {content}.
Justification: {...}.

---

# 4. Notation and Data Preprocessing

## 4.1 Notation

| Symbol | Meaning | Unit |
| --- | --- | --- |
| $x$ | {meaning} | {unit} |
| $y$ | {meaning} | {unit} |
| $\alpha$ | {meaning} | {unit} |

## 4.2 Data Preprocessing

> Data-driven problems: full EDA covering missing values, outliers,
> distributions, correlation, group comparisons, all grounded in the coder's
> actual `print` outputs.
>
> Physics / mechanism problems: skip descriptive statistics; replace with
> a "key parameters table + geometric derivation + dimensional check +
> physical consistency verification".

---

# 5. Model Formulation and Solution

## 5.1 Problem 1: Model Formulation and Solution

### 5.1.1 Model Formulation

{Brief description of the model.}

$$
\min_{x \in \mathcal{X}} \; f(x) = \sum_{i=1}^{N} c_i x_i \quad
\text{s.t.} \; g_j(x) \le 0,\, j = 1, \dots, M
$$

Parameter sources: $c_i$ is estimated from {data source}; $g_j$ comes from
{physical / problem-specified} constraints.

### 5.1.2 Model Solution

Solution procedure: {steps}. Results:

| Metric | Value |
| --- | --- |
| {metric 1} | {value} |
| {metric 2} | {value} |

![Problem 1 main result](fig_q1_main.png)

Interpretation 1: {trend grounded in print output}.
Interpretation 2: {key inflection grounded in print output}.
Interpretation 3: {explanation tied to modeling rationale}.

## 5.2 Problem 2: Model Formulation and Solution

(Same structure, ~600 words each.)

## 5.N Problem N

---

# 6. Sensitivity Analysis

We perturbed key parameters $\{\theta_1, \theta_2, \theta_3\}$ within ±20%
and measured the response in {R² / RMSE / objective value}.

![Sensitivity analysis](fig_sensitivity.png)

Interpretation: {which parameter is most sensitive, quantified}; {how other
parameters affect the result}; {conclusion on robustness tied to the model}.

---

# 7. Model Evaluation, Improvement and Generalization

## 7.1 Strengths

First, {strength 1, evidence}. Second, {strength 2, evidence}. Third,
{strength 3, evidence}. Fourth, {strength 4, evidence}.

## 7.2 Weaknesses

First, {weakness 1, evidence}. Second, {weakness 2, evidence}.

## 7.3 Improvement and Generalization

{Possible extensions to other scenarios; state preconditions for each.}

---

# References

{[^1] full reference}

{[^2] full reference}
