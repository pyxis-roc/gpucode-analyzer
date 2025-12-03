#pragma once
#include <stdint.h>

#define S2R(dst, src) dst = src

#define IMAD_U32(dst, src1, src2, src3) dst = src1 * src2 + src3
#define IMAD(dst, src1, src2, src3) dst = src1 * src2 + src3

#define IMAD_MOV_U32(dst, src1, src2, src3) IMAD(dst, src1, src2, src3)
#define IMAD_IADD_U32(dst, src1, src2, src3) IMAD(dst, src1, src2, src3)
#define IMAD_SHL_U32(dst, src1, src2, src3) IMAD(dst, src1, src2, src3)
#define IMAD_MOV(dst, src1, src2, src3) IMAD(dst, src1, src2, src3)
#define IMAD_IADD(dst, src1, src2, src3) IMAD(dst, src1, src2, src3)

#define IADD3(dst, src1, src2, src3) dst = src1 + src2 + src3

#define EXIT() goto label_exit
#define BRA(label) goto label
#define CALL_REL_NOINC(label) goto label

#define ISETP_GT_AND_D0(dst0, dst1, src1, src2, src3) dst0 = ((int32_t) src1 > (int32_t) src2) && src3
#define ISETP_GT_AND_D1(dst0, dst1, src1, src2, src3) dst1 = !dst0

#define ISETP_LT_AND_D0(dst0, dst1, src1, src2, src3) dst0 = ((int32_t) src1 < (int32_t) src2) && src3
#define ISETP_LT_AND_D1(dst0, dst1, src1, src2, src3) dst1 = !dst0

#define ISETP_GE_AND_D0(dst0, dst1, src1, src2, src3) dst0 = ((int32_t) src1 >= (int32_t) src2) && src3
#define ISETP_GE_AND_D1(dst0, dst1, src1, src2, src3) dst1 = !dst0

#define ISETP_GE_U32_AND_D0(dst0, dst1, src1, src2, src3) dst0 = (src1 >= src2) && src3
#define ISETP_GE_U32_AND_D1(dst0, dst1, src1, src2, src3) dst1 = !dst0

#define ISETP_GT_U32_AND_D0(dst0, dst1, src1, src2, src3) dst0 = (src1 > src2) && src3
#define ISETP_GT_U32_AND_D1(dst0, dst1, src1, src2, src3) dst1 = !dst0

#define ISETP_NE_U32_AND_D0(dst0, dst1, src1, src2, src3) dst0 = (src1 != src2) && src3
#define ISETP_NE_U32_AND_D1(dst0, dst1, src1, src2, src3) dst1 = !dst0

#define ISETP_NE_AND_D0(dst0, dst1, src1, src2, src3) dst0 = ((int32_t) src1 != (int32_t) src2) && src3
#define ISETP_NE_AND_D1(dst0, dst1, src1, src2, src3) dst1 = !dst0


#define ISETP_EQ_U32_AND_D0(dst0, dst1, src1, src2, src3) dst0 = (src1 == src2) && src3
#define ISETP_EQ_U32_AND_D1(dst0, dst1, src1, src2, src3) dst1 = !dst0


#define UISETP_GE_U32_AND_D0(dst0, dst1, src1, src2, src3) ISETP_GE_U32_AND_D0(dst0, dst1, src1, src2, src3)
#define UISETP_GE_U32_AND_D1(dst0, dst1, src1, src2, src3) ISETP_GE_U32_AND_D1(dst0, dst1, src1, src2, src3)

#define UISETP_GT_U32_AND_D0(dst0, dst1, src1, src2, src3) ISETP_GT_U32_AND_D0(dst0, dst1, src1, src2, src3)
#define UISETP_GT_U32_AND_D1(dst0, dst1, src1, src2, src3) ISETP_GT_U32_AND_D1(dst0, dst1, src1, src2, src3)


#define UISETP_NE_U32_AND_D0(dst0, dst1, src1, src2, src3) ISETP_NE_U32_AND_D0(dst0, dst1, src1, src2, src3)
#define UISETP_NE_U32_AND_D1(dst0, dst1, src1, src2, src3) ISETP_NE_U32_AND_D1(dst0, dst1, src1, src2, src3)

#define UISETP_LT_AND_D0(dst0, dst1, src1, src2, src3) ISETP_LT_AND_D0(dst0, dst1, src1, src2, src3)
#define UISETP_LT_AND_D1(dst0, dst1, src1, src2, src3) ISETP_LT_AND_D1(dst0, dst1, src1, src2, src3)


#define UMOV(dst, src) dst = src
#define UIADD3(dst, src1, src2, src3) dst = src1 + src2 + src3
#define LOP3_LUT(dst, src1, src2, src3, immLut) dst = logical_op3(src1, src2, src3, immLut)
#define ULOP3_LUT(dst, src1, src2, src3, immLut) dst = logical_op3(src1, src2, src3, immLut)

// pretend PLOP3 is LOP3?
#define PLOP3_LUT(dst1, dst2, src1, src2, src3, immLut, src4) dst1 = logical_op3(src1, src2, src3, immLut)

#define CS2R(dst, src) dst = src
#define IMNMX_U32(dst, src1, src2, mnpred) if(mnpred) { dst = src1 < src2 ? src1 : src2; } else { dst = src1 > src2 ? src1 : src2; } // TODO
#define ULDC(dst, src) dst = src

#define concat_u32(hi, lo) ((((uint64_t) hi) << 32) | (uint64_t) lo)

#define rotate_right_64(val, rot) rot == 64 ? val : ((val << (64 - rot)) | (val >> rot))


#define SHF_R_U32_HI(dst, src1, rot, src2) dst = ((rotate_right_64(concat_u32(src2, src1), rot) >> 32) & 0xFFFFFFFFUL)
#define USHF_R_U32_HI(dst, src1, rot, src2) SHF_R_U32_HI(dst, src1, rot, src2)

#define SEL(dst, src1, src2, pred) dst = pred ? src1 : src2
#define USEL(dst, src1, src2, pred) SEL(dst, src1, src2, pred)

// TODO: is hi taken after the shift or after the add?
#define LEA_HI(dst, pred, alo, b, ahi, imm_shift) dst = ((concat_u32(ahi, alo) << imm_shift) + b) >> 32

#define P2R(dst, ign_PR, ign_RZ, pred_set) dst = pred_set
