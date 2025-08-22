try:
    from ..openmathinst_utils import extract_answer, math_equal
except:
    from utils.openmathinst_utils import extract_answer, math_equal

import ray
from ray.exceptions import GetTimeoutError
from math_verify import verify, parse
from typing import Union

def math_equal_ray(
    prediction: Union[bool, float, str],
    reference: Union[float, str],
    include_percentage: bool = True,
    tolerance: float = 1e-4,
    timeout: float = 10.0,
    check_antlr_version: bool = True
) -> bool:
    return math_equal(prediction, reference, include_percentage, tolerance, timeout, check_antlr_version)

def verify_ray(
    gold, 
    target, 
    float_rounding: int=6,
    numeric_precision: int=15,
    strict: bool=True,
    timeout_seconds: int=3
) -> bool:
    return verify(gold, target, float_rounding, numeric_precision, strict, timeout_seconds)

def reward_func(data_source, solution_str, ground_truth, extra_info) -> float:
    if "</think>" in solution_str:
        # to avoid the case that boxed appears in both the thinking and the solution
        solution_str = solution_str.split("</think>")[-1]
        format_correct = True
    else:
        # format reward
        format_correct = False

    omi_pred = None
    omi_correct = False
    mathv_pred = None
    mathv_correct = False
    if format_correct:
        # omi
        try:
            omi_pred = extract_answer(solution_str, extract_from_boxed=True)
            omi_correct_ref = math_equal_ray.remote(omi_pred, ground_truth, check_antlr_version=False)
            omi_correct = ray.get(omi_correct_ref, timeout=10.0)
        except GetTimeoutError as e:
            ray.cancel(omi_correct_ref, force=True)
            omi_correct = False
        except Exception:
            omi_correct = False

        # math
        try:
            mathv_pred = parse(solution_str)
            mathv_correct_ref = verify_ray.remote(parse(f"\\boxed{{${ground_truth}$}}"), mathv_pred)
            mathv_correct = ray.get(mathv_correct_ref, timeout=10.0)
        except GetTimeoutError as e:
            ray.cancel(mathv_correct_ref, force=True)
            mathv_correct = False
        except Exception:
            mathv_correct = False

    acc = format_correct and (omi_correct or mathv_correct)
    score = 1.0 if acc else -1.0

    return {
        "score": score,
        "acc": acc,
        "pred": omi_pred,
        "omi_correct": omi_correct,
        "mathv_correct": mathv_correct
    }

def my_reward_func(data_source, solution_str, ground_truth, extra_info) -> float:
    omi_pred = None
    omi_correct = False
    mathv_pred = None
    mathv_correct = False
    
    # omi
    try:
        omi_pred = extract_answer(solution_str, extract_from_boxed=True)
        omi_correct_ref = math_equal(omi_pred, ground_truth, check_antlr_version=False)
        omi_correct = omi_correct_ref
    except Exception:
        omi_correct = False

    # math
    try:
        mathv_pred = parse(solution_str)
        mathv_correct_ref = verify_ray(parse(f"\\boxed{{${ground_truth}$}}"), mathv_pred)
        mathv_correct = mathv_correct_ref
    except Exception:
        mathv_correct = False

    acc = omi_correct or mathv_correct
    score = 1.0 if acc else -1.0

    return {
        "score": score,
        "acc": acc
    }

if __name__ == "__main__":
    print(my_reward_func("_", "asdada\\boxed{3/2}", "1.50", None))
