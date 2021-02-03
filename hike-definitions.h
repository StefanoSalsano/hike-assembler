#include <stdio.h>
#include <string.h>
#include <netinet/in.h>
#include <linux/if_ether.h>
#include <linux/in6.h>
#include <linux/ipv6.h>
#include <time.h>
#include <assert.h>
#include <stdlib.h>
#include <errno.h>

/* New ID specs:
 * an elem_ID (uprog ID/chain ID) is structured as follows:
 *
 * 	k2 k1 k0 m5 m4 m3 m2 m1 m0
 *
 *  - A valid UPROG ID MUST set to 0 every k_j bits j in [0..2].
 *    Therefore, we can have a total of 2^6 possibile UPROG IDs, i.e.:
 *
 * 		b000 000110 = 0x06 is a valid UPROG ID;
 * 		b011 000110 = 0x36 is NOT a valid UPROG ID;
 *
 *  - A valid CHAIN ID MUST set at least one of the k2 k1 k0 bits to 1.
 *    No restrictions for m5, m4, ..., m0 for a CHAIN ID.
 *
 *  	b001 001010 = 0x4a is a valid CHAIN ID;
 *  	b000 001010	= 0x0a is NOT a valid CHAIN ID.
 */
#define UPROG_MASK_BITS		6
#define CHAIN_MASK_BITS		9

/* XXX: note those values depend on the UPROG_MASK_BITS and CHAIN_MASK_BITS */
#define CHAIN_DEFAULT_ID	0x7defc1c0

#define BIT(x)								\
	((__u32)(((__u32)1) << ((__u32)(x))))

#define ELEM_ID_GEN_MASK_U32(__nbits) 					\
		((__u32)(BIT(__nbits) - ((__u32)1)))

#define UPROG_MASK	ELEM_ID_GEN_MASK_U32(UPROG_MASK_BITS)
#define CHAIN_MASK	ELEM_ID_GEN_MASK_U32(CHAIN_MASK_BITS)

#define NOSIGN_CAST_TO_64(v)	(((__u64)(v)) & ((__u64)0xffffffff))


/* ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ */

/* Structure of an hike_insn
 *
 *
 * ~~~~~~~~~~~~~~~
 *  opcode layout
 * ~~~~~~~~~~~~~~~
 * Last 3 bits of the opcode field identify the "instruction class".
 *
 * ALU/ALU64/JMP opcode structure:
 * MSB      LSB
 * +----+-+---+
 * |op  |s|cls|
 * +----+-+---+
 *
 * if the s bit is zero, then the source operand is imm. If s is one, then the
 * source operand is src. The op field specifies which ALU or branch operation
 * is to be performed.
 *
 * MSB									    LSB
 * +--------------+-----------------+------------+------------+---------------+
 * | imm (32 bit) | offset (16 bit) | src (4bit) | dst (4bit) | opcode (8bit) |
 * +--------------+-----------------+------------+------------+---------------+
 *
 *
 *  extended instruction only for JUMP_TAIL_CALL to HIKe program/chain
 *
 * MSB							   		    LSB
 * +--------------------------------+-------------------------+---------------+
 * |           arg (32 bit)         |      id (24 bit)        | opcode (8bit) |
 * +--------------------------------+-------------------------+---------------+
 *
 * dst and src are index of registers:
 * 	A = 0x0
 * 	B = 0x1
 * 	W = 0x2
 *
 * Opcode examples:
 *
 *  Mnemonic				| Opcode      | Pseudocode
 *  call id, arg			| opcode 0x85 | function call id:arg
 *  jeq  dst, imm, +off		        | opcode 0x15 | PC += off, if dst == imm
 *
 */

struct hike_insn_core {
	__u8	code;
	__u8	dst_reg:	4;
	__u8	src_reg:	4;
	__s16	off;
};

struct hike_insn_ext_core {
	__u32	code:		8;
	__u32	off:		24;
};

struct hike_insn {
	union {
		struct hike_insn_core c;
		struct hike_insn_ext_core ec;
	} u;
#define hic_code	u.c.code
#define hic_dst		u.c.dst_reg
#define hic_src		u.c.src_reg
#define hic_off		u.c.off

#define hiec_code	u.ec.code
#define hiec_off	u.ec.off

	__s32 imm;
};

enum {
	HIKE_REG_A = 0,
	HIKE_REG_B,
	HIKE_REG_W,
};

/* instruction classes */
#define HIKE_CLASS(code)		((code) & 0x07)
#define	HIKE_JMP64			0x05	/* 64 bit between DST imm32/SRC */
#define HIKE_ALU64			0x07	/* ALU mode in 64 bit (double word with) */

#define HIKE_OP(code)			((code) & 0xf0)

/* jmp encodings */
#define HIKE_CALL			0x80
#define HIKE_TAIL_CALL			0xf0
#define HIKE_EXIT			0x90

/* jmp fields */
#define HIKE_JA 			0x00
#define HIKE_JEQ 			0x10	/* == */
#define	HIKE_JGT 			0x20	/* >  */
#define	HIKE_JGE 			0x30	/* >= */
#define	HIKE_JNE 			0x50	/* != */
#define HIKE_JLT 			0xa0	/* <  */
#define HIKE_JLE 			0xb0	/* <= */

/* alu fields */
#define HIKE_ADD			0x00
#define HIKE_MOV			0xb0

#define HIKE_SRC(code)   		((code) & 0x08)
#define HIKE_K				0x00
#define	HIKE_X				0x08
	/* those structure should be created, zeroed and then f */


#define HIKE_RAW_INSN(CODE, DST, SRC, OFF, IMM)				\
	((struct hike_insn) {						\
		.u = {							\
			.c = {						\
				.code = CODE,				\
				.dst_reg = DST,				\
				.src_reg = SRC,				\
				.off = OFF,				\
			}						\
		},							\
		.imm = IMM,                                       	\
	})

#define HIKE_RAW_EXT_INSN(CODE, OFF, IMM)				\
	((struct hike_insn) {						\
		.u = {							\
			.ec = {						\
				.code = CODE,				\
				.off = OFF,				\
			}						\
		},							\
		.imm = IMM,                                       	\
	})


/* Supported instructions at 2020-01-30 */
#define HIKE_JMP64_IMM_INSN(OP, DST, OFF, IMM)				\
	HIKE_RAW_INSN(HIKE_JMP64 | HIKE_OP(OP) | HIKE_K, DST,		\
		      0, OFF, IMM)

#define HIKE_JEQ64_IMM_INSN(DST, OFF, IMM)				\
	HIKE_JMP64_IMM_INSN(HIKE_JEQ, DST, OFF, IMM)

#define HIKE_JNE64_IMM_INSN(DST, OFF, IMM)				\
	HIKE_JMP64_IMM_INSN(HIKE_JNE, DST, OFF, IMM)

#define HIKE_JGT64_IMM_INSN(DST, OFF, IMM)				\
	HIKE_JMP64_IMM_INSN(HIKE_JGT, DST, OFF, IMM)

#define HIKE_JGE64_IMM_INSN(DST, OFF, IMM)				\
	HIKE_JMP64_IMM_INSN(HIKE_JGE, DST, OFF, IMM)

#define HIKE_JLT64_IMM_INSN(DST, OFF, IMM)				\
	HIKE_JMP64_IMM_INSN(HIKE_JLT, DST, OFF, IMM)

#define HIKE_JLE64_IMM_INSN(DST, OFF, IMM)				\
	HIKE_JMP64_IMM_INSN(HIKE_JLE, DST, OFF, IMM)

#define HIKE_JNE64_IMM_INSN(DST, OFF, IMM)				\
	HIKE_JMP64_IMM_INSN(HIKE_JNE, DST, OFF, IMM)

#define HIKE_JA64_IMM_INSN(OFF)						\
	HIKE_JMP64_IMM_INSN(HIKE_JA, 0, OFF, 0)

#define HIKE_ALU64_IMM_INSN(OP, DST, IMM)				\
	HIKE_RAW_INSN(HIKE_ALU64 | HIKE_OP(OP) | HIKE_K, DST,		\
		      0, 0, IMM)					\

#define HIKE_MOV64_IMM_INSN(DST, IMM)					\
	HIKE_ALU64_IMM_INSN(HIKE_MOV, DST, IMM)

#define HIKE_ADDS64_IMM_INSN(DST, IMM)					\
	HIKE_ALU64_IMM_INSN(HIKE_ADD, DST, IMM)

#define HIKE_ALU64_REG_INSN(OP, DST, SRC)				\
	HIKE_RAW_INSN(HIKE_ALU64 | HIKE_OP(OP) | HIKE_X, DST,		\
		      SRC, 0, 0)

#define HIKE_MOV64_REG_INSN(DST, SRC)					\
	HIKE_ALU64_REG_INSN(HIKE_MOV, DST, SRC)


#define HIKE_TAIL_CALL_ELEM_INSN(OFF, IMM)				\
	HIKE_RAW_EXT_INSN(HIKE_JMP64 | HIKE_OP(HIKE_TAIL_CALL),		\
			  OFF, IMM)					\

#define HIKE_EXIT_INSN() 						\
	HIKE_RAW_INSN(HIKE_JMP64 | HIKE_EXIT, 0, 0, 0, 0)


/* ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ */

#define HIKE_CHAIN_NINSN_MAX			16
#define HCHAIN_FRAME_REGS_U8_MAX 		32

struct hike_chain_regmem {
	__u64	reg_A;			/* index 0 */
	__u64	reg_B;			/* index 1 */
	__u64	reg_W;			/* index 2 */

	__u8	mem[HCHAIN_FRAME_REGS_U8_MAX];
};

/* this structure is aligned to 256 byte.. if we are lucky enough it will fit
 * completely two cache rows...
 */
struct hike_chain {
	/* first line of cache 64 bytes */
	__s32 chain_id;
	__u16 ninsn;
	__u16 upc;

	/* registers and private memory for an HIKe Microprogram/Chain */
	struct hike_chain_regmem regmem;

	/* second line of cache 64 bytes; two separate cache lines avoid false
	 * false sharing. The set of instruction is mostly read while the set of
	 * registers and "memory" are mixed read/write
	 */
	struct hike_insn insns[HIKE_CHAIN_NINSN_MAX];
};

/* ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ */

void hike_chain_dump_hex(const void* data, size_t size)
{
	size_t i;

	for (i = 0; i < size; ++i) {
		if (!(i & 0xf))
			printf("%02X", ((unsigned char *)data)[i]);
		else
			printf(" %02X", ((unsigned char *)data)[i]);

		if ((i & 0xf) == 0x7)
			printf(" ");

		if ((i & 0xf) == 0xf)
			printf("\n");
	}
	printf("\n");
}

void assemble(struct hike_chain *hc)
{
	int i;

	for (i = 0; i < HIKE_CHAIN_NINSN_MAX; ++i) {
		if ((*(__u64 *)&hc->insns[i]) == 0)
			break;
	}

	/* set the effective number of instructions */
	hc->ninsn = i;

	hike_chain_dump_hex(&hc->chain_id, sizeof(hc->chain_id));
	hike_chain_dump_hex(hc, sizeof(*hc));
}

void samples()
{
	/* we rely on the fact that unused fields are zeroed by the env... */
	struct hike_chain chain_65 = {
		.chain_id = 65,
		.insns = {
				HIKE_MOV64_IMM_INSN(HIKE_REG_A, 0),
				HIKE_JGT64_IMM_INSN(HIKE_REG_A, 3, 4),
				HIKE_TAIL_CALL_ELEM_INSN(8, 17),
				HIKE_ADDS64_IMM_INSN(HIKE_REG_A, 1),
				HIKE_JA64_IMM_INSN(-4),
				HIKE_MOV64_IMM_INSN(HIKE_REG_W, 0xa),
				HIKE_TAIL_CALL_ELEM_INSN(66, 0),
				HIKE_EXIT_INSN(),
		},
	};

	struct hike_chain chain_66 = {
		.chain_id = 66,
		.insns = {
				HIKE_MOV64_IMM_INSN(HIKE_REG_A, 65536),
				HIKE_TAIL_CALL_ELEM_INSN(9, 1987),
				HIKE_EXIT_INSN(),
		},
	};

	assemble(&chain_65);
	assemble(&chain_66);
}

int main() {
	printf("Very very dirty HIKe assembler\n\n");

	samples();

	return 0;
}
