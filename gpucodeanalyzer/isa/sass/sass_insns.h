#pragma once


#define S2R(dst, src) dst = src

#define IMAD_U32(dst, src1, src2, src3) dst = src1 * src2 + src3
#define IMAD(dst, src1, src2, src3) dst = src1 * src2 + src3

#define IMAD_MOV_U32(dst, src1, src2, src3) IMAD(dst, src1, src2, src3)
#define IMAD_IADD_U32(dst, src1, src2, src3) IMAD(dst, src1, src2, src3)
#define IMAD_SHL_U32(dst, src1, src2, src3) IMAD(dst, src1, src2, src3)

#define IADD3(dst, src1, src2, src3) dst = src1 + src2 + src3

#define EXIT() return
#define BRA(label) goto label

#define ISETP_GT_AND_D0(dst0, dst1, src1, src2, src3) dst0 = (src1 > src2) && src3
#define ISETP_GT_AND_D1(dst0, dst1, src1, src2, src3) dst1 = !dst0

#define ISETP_GE_AND_D0(dst0, dst1, src1, src2, src3) dst0 = (src1 >= src2) && src3
#define ISETP_GE_AND_D1(dst0, dst1, src1, src2, src3) dst1 = !dst0
