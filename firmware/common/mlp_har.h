/**
 * @file mlp_har.h
 * @brief Suy luan MLP 561-64-6 (FP32) cho UCI HAR.
 *
 * Trong so nam trong mlp_weights.h (sinh tu ml/results/mlp_seed42.pt).
 */
#ifndef MLP_HAR_H
#define MLP_HAR_H

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Tinh 6 logit tu 561 dac trung goc.
 *
 * @param x      561 float32 dau vao (khong padding, khong chuan hoa).
 * @param logits 6 float32 dau ra.
 * @return lop argmax 0..5 (hoa -> chi so nho hon), hoac -2 neu con tro NULL
 *         hay co logit khong huu han (cung quy uoc voi mambahar.c).
 */
int mlp_har_forward_logits(const float *x, float *logits);

#ifdef __cplusplus
}
#endif

#endif /* MLP_HAR_H */
