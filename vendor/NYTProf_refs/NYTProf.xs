/* vim: ts=8 sw=4 expandtab:
 * ************************************************************************
 * This file is part of the Devel::NYTProf package.
 * Copyright 2008 Adam J. Kaplan, The New York Times Company.
 * Copyright 2009-2010 Tim Bunce, Ireland.
 * Released under the same terms as Perl 5.8
 * See http://metacpan.org/release/Devel-NYTProf/
 *
 * Contributors:
 * Tim Bunce, http://blog.timbunce.org
 * Nicholas Clark,
 * Adam Kaplan, akaplan at nytimes.com
 * Steve Peters, steve at fisharerojo.org
 *
 * ************************************************************************
 */
#define PERL_NO_GET_CONTEXT                       /* we want efficiency */

#include "EXTERN.h"
#include "perl.h"
#include "XSUB.h"

#include "FileHandle.h"
#include "NYTProf.h"

#ifndef NO_PPPORT_H
#define NEED_my_snprintf_GLOBAL
#define NEED_newRV_noinc_GLOBAL
#define NEED_sv_2pv_flags
#define NEED_newSVpvn_flags
#define NEED_my_strlcat
#   include "ppport.h"
#endif

/* Until ppport.h gets this:  */
#ifndef memEQs
#  define memEQs(s1, l, s2) \
          (sizeof(s2)-1 == l && memEQ(s1, ("" s2 ""), (sizeof(s2)-1)))
#endif

#ifdef USE_HARD_ASSERT
#undef NDEBUG
#include <assert.h>
#endif

#if !defined(OutCopFILE)
#    define OutCopFILE CopFILE
#endif

#ifndef gv_fetchfile_flags  /* added in perl 5.009005 */
/* we know our uses don't contain embedded nulls, so we just need to copy to a
 * buffer so we can add a trailing null byte */
#define gv_fetchfile_flags(a,b,c)   gv_fetchfile_flags(a,b,c)
static GV *
gv_fetchfile_flags(pTHX_ const char *const name, const STRLEN namelen, const U32 flags) {
    char buf[2000];
    if (namelen >= sizeof(buf)-1)
        croak("panic: gv_fetchfile_flags overflow");
    memcpy(buf, name, namelen);
    buf[namelen] = '\0'; /* null-terminate */
    return gv_fetchfile(buf);
}
#endif

#ifndef OP_SETSTATE
#define OP_SETSTATE OP_NEXTSTATE
#endif
#ifndef PERLDBf_SAVESRC
#define PERLDBf_SAVESRC PERLDBf_SUBLINE
#endif
#ifndef PERLDBf_SAVESRC_NOSUBS
#define PERLDBf_SAVESRC_NOSUBS 0
#endif
#ifndef CvISXSUB
#define CvISXSUB CvXSUB
#endif

#if (PERL_VERSION < 8) || ((PERL_VERSION == 8) && (PERL_SUBVERSION < 8))
/* If we're using DB::DB() instead of opcode redirection with an old perl
 * then PL_curcop in DB() will refer to the DB() wrapper in Devel/NYTProf.pm
 * so we'd have to crawl the stack to find the right cop. However, for some
 * reason that I don't pretend to understand the following expression works:
 */
#define PL_curcop_nytprof (opt_use_db_sub ? ((cxstack + cxstack_ix)->blk_oldcop) : PL_curcop)
#else
#define PL_curcop_nytprof PL_curcop
#endif

#define OP_NAME_safe(op) ((op) ? OP_NAME(op) : "NULL")

#ifdef I_SYS_TIME
#include <sys/time.h>
#endif
#include <stdio.h>

#ifdef HAS_ZLIB
#include <zlib.h>
#define default_compression_level 6
#else
#define default_compression_level 0
#endif
#ifndef ZLIB_VERSION
#define ZLIB_VERSION "0"
#endif

#ifndef NYTP_MAX_SUB_NAME_LEN
#define NYTP_MAX_SUB_NAME_LEN 500
#endif

#define NYTP_FILE_MAJOR_VERSION 5
#define NYTP_FILE_MINOR_VERSION 0

#define NYTP_START_NO            0
#define NYTP_START_BEGIN         1
#define NYTP_START_CHECK_unused  2  /* not used */
#define NYTP_START_INIT          3
#define NYTP_START_END           4

#define NYTP_OPTf_ADDPID         0x0001 /* append .pid to output filename */
#define NYTP_OPTf_OPTIMIZE       0x0002 /* affect $^P & 0x04 */
#define NYTP_OPTf_SAVESRC        0x0004 /* copy source code lines into profile data */
#define NYTP_OPTf_ADDTIMESTAMP   0x0008 /* append timestamp to output filename */

#define NYTP_FIDf_IS_PMC         0x0001 /* .pm probably really loaded as .pmc */
#define NYTP_FIDf_VIA_STMT       0x0002 /* fid first seen by stmt profiler */
#define NYTP_FIDf_VIA_SUB        0x0004 /* fid first seen by sub profiler */
#define NYTP_FIDf_IS_AUTOSPLIT   0x0008 /* fid is an autosplit (see AutoLoader) */
#define NYTP_FIDf_HAS_SRC        0x0010 /* src is available to profiler */
#define NYTP_FIDf_SAVE_SRC       0x0020 /* src will be saved by profiler, if NYTP_FIDf_HAS_SRC also set */
#define NYTP_FIDf_IS_ALIAS       0x0040 /* fid is clone of the 'parent' fid it was autosplit from */
#define NYTP_FIDf_IS_FAKE        0x0080 /* eg dummy caller of a string eval that doesn't have a filename */
#define NYTP_FIDf_IS_EVAL        0x0100 /* is an eval */

/* indices to elements of the file info array */
#define NYTP_FIDi_FILENAME       0
#define NYTP_FIDi_EVAL_FID       1
#define NYTP_FIDi_EVAL_LINE      2
#define NYTP_FIDi_FID            3
#define NYTP_FIDi_FLAGS          4
#define NYTP_FIDi_FILESIZE       5
#define NYTP_FIDi_FILEMTIME      6
#define NYTP_FIDi_PROFILE        7
#define NYTP_FIDi_EVAL_FI        8
#define NYTP_FIDi_HAS_EVALS      9
#define NYTP_FIDi_SUBS_DEFINED  10
#define NYTP_FIDi_SUBS_CALLED   11
#define NYTP_FIDi_elements      12   /* highest index, plus 1 */

/* indices to elements of the sub info array (report-side only) */
#define NYTP_SIi_FID             0   /* fid of file sub was defined in */
#define NYTP_SIi_FIRST_LINE      1   /* line number of first line of sub */    
#define NYTP_SIi_LAST_LINE       2   /* line number of last line of sub */    
#define NYTP_SIi_CALL_COUNT      3   /* number of times sub was called */
#define NYTP_SIi_INCL_RTIME      4   /* incl real time in sub */
#define NYTP_SIi_EXCL_RTIME      5   /* excl real time in sub */
#define NYTP_SIi_SUB_NAME        6   /* sub name */
#define NYTP_SIi_PROFILE         7   /* ref to profile object */
#define NYTP_SIi_REC_DEPTH       8   /* max recursion call depth */
#define NYTP_SIi_RECI_RTIME      9   /* recursive incl real time in sub */
#define NYTP_SIi_CALLED_BY      10   /* { fid => { line => [...] } } */
#define NYTP_SIi_elements       11   /* highest index, plus 1 */

/* indices to elements of the sub call info array */
/* XXX currently ticks are accumulated into NYTP_SCi_*_TICKS during profiling
 * and then NYTP_SCi_*_RTIME are calculated and output. This avoids float noise
 * during profiling but we should really output ticks so the reporting side
 * can also be more accurate when merging subs, for example.
 * That'll probably need a file format bump and thus also a major version bump.
 * Will need coresponding changes to NYTP_SIi_* as well.
 */
#define NYTP_SCi_CALL_COUNT      0   /* count of calls to sub */    
#define NYTP_SCi_INCL_RTIME      1   /* inclusive real time in sub (set from NYTP_SCi_INCL_TICKS) */
#define NYTP_SCi_EXCL_RTIME      2   /* exclusive real time in sub (set from NYTP_SCi_EXCL_TICKS) */
#define NYTP_SCi_INCL_TICKS      3   /* inclusive ticks in sub */
#define NYTP_SCi_EXCL_TICKS      4   /* exclusive ticks in sub */
#define NYTP_SCi_RECI_RTIME      5   /* recursive incl real time in sub */
#define NYTP_SCi_REC_DEPTH       6   /* max recursion call depth */
#define NYTP_SCi_CALLING_SUB     7   /* name of calling sub */
#define NYTP_SCi_elements        8   /* highest index, plus 1 */


/* we're not thread-safe (or even multiplicity safe) yet, so detect and bail */
#ifdef MULTIPLICITY
static PerlInterpreter *orig_my_perl;
#endif


#define MAX_HASH_SIZE 512

typedef struct hash_entry Hash_entry;

struct hash_entry {
    unsigned int id;
    char* key;
    int key_len;
    Hash_entry* next_entry;
    Hash_entry* next_inserted;  /* linked list in insertion order */
};

typedef struct hash_table {
    Hash_entry** table;
    char *name;
    unsigned int size;
    unsigned int entry_struct_size;
    Hash_entry* first_inserted;
    Hash_entry* prior_inserted; /* = last_inserted before the last insertion */
    Hash_entry* last_inserted;
    unsigned int next_id;       /* starts at 1, 0 is reserved */
} Hash_table;

typedef struct {
    Hash_entry he;
    unsigned int eval_fid;
    unsigned int eval_line_num;
    unsigned int file_size;
    unsigned int file_mtime;
    unsigned int fid_flags;
    char *key_abs;
    /* update autosplit logic in get_file_id if fields are added or changed */
} fid_hash_entry;

static Hash_table fidhash = { NULL, "fid", MAX_HASH_SIZE, sizeof(fid_hash_entry), NULL, NULL, NULL, 1 };

typedef struct {
    Hash_entry he;
} str_hash_entry;
static Hash_table strhash = { NULL, "str", MAX_HASH_SIZE, sizeof(str_hash_entry), NULL, NULL, NULL, 1 };
/* END Hash table definitions */


/* defaults */
static NYTP_file out;

/* options and overrides */
static char PROF_output_file[MAXPATHLEN+1] = "nytprof.out";
static unsigned int profile_opts = NYTP_OPTf_OPTIMIZE | NYTP_OPTf_SAVESRC;
static int profile_start = NYTP_START_BEGIN;      /* when to start profiling */

static char const *nytp_panic_overflow_msg_fmt = "panic: buffer overflow of %s on '%s' (see TROUBLESHOOTING section of the NYTProf documentation)";

struct NYTP_options_t {
    const char *option_name;
    IV    option_iv;
    char *option_pv;    /* strdup'd */
};

/* XXX boolean options should be moved into profile_opts */
static struct NYTP_options_t options[] = {
#define profile_usecputime options[0].option_iv
    { "usecputime", 0, NULL },
#define profile_subs options[1].option_iv
    { "subs", 1, NULL },                                /* subroutine times */
#define profile_blocks options[2].option_iv
    { "blocks", 0, NULL },                              /* block and sub *exclusive* times */
#define profile_leave options[3].option_iv
    { "leave", 1, NULL },                               /* correct block end timing */
#define embed_fid_line options[4].option_iv
    { "expand", 0, NULL },
#define trace_level options[5].option_iv
    { "trace", 0, NULL },
#define opt_use_db_sub options[6].option_iv
    { "use_db_sub", 0, NULL },
#define compression_level options[7].option_iv
    { "compress", default_compression_level, NULL },
#define profile_clock options[8].option_iv
    { "clock", -1, NULL },
#define profile_stmts options[9].option_iv
    { "stmts", 1, NULL },                              /* statement exclusive times */
#define profile_slowops options[10].option_iv
    { "slowops", 2, NULL },                            /* slow opcodes, typically system calls */
#define profile_findcaller options[11].option_iv
    { "findcaller", 0, NULL },                         /* find sub caller instead of trusting outer */
#define profile_forkdepth options[12].option_iv
    { "forkdepth", -1, NULL },                         /* how many generations of kids to profile */
#define opt_perldb options[13].option_iv
    { "perldb", 0, NULL },                             /* force certain PL_perldb value */
#define opt_nameevals options[14].option_iv
    { "nameevals", 1, NULL },                          /* change $^P 0x100 bit */
#define opt_nameanonsubs options[15].option_iv
    { "nameanonsubs", 1, NULL },                       /* change $^P 0x200 bit */
#define opt_calls options[16].option_iv
    { "calls", 1, NULL },                              /* output call/return event stream */
#define opt_evals options[17].option_iv
    { "evals", 0, NULL }                               /* handling of string evals - TBD XXX */
};
/* XXX TODO: add these to options:
    if (strEQ(option, "file")) {
        strncpy(PROF_output_file, value, MAXPATHLEN);
    else if (strEQ(option, "log")) {
    else if (strEQ(option, "start")) {
    else if (strEQ(option, "addpid")) {
    else if (strEQ(option, "optimize") || strEQ(option, "optimise")) {
    else if (strEQ(option, "savesrc")) {
    else if (strEQ(option, "endatexit")) {
    else if (strEQ(option, "libcexit")) {
and write the options to the stream when profiling starts.
*/


/* time tracking */
#ifdef WIN32
/* win32_gettimeofday has ~15 ms resolution on Win32, so use
 * QueryPerformanceCounter which has us or ns resolution depending on
 * motherboard and OS. Comment this out to use the old clock.
 */
#  define HAS_QPC
#endif /* WIN32 */

#ifdef HAS_CLOCK_GETTIME

/* http://www.freebsd.org/cgi/man.cgi?query=clock_gettime
 * http://webnews.giga.net.tw/article//mailing.freebsd.performance/710
 * http://sean.chittenden.org/news/2008/06/01/
 * Explanation of why gettimeofday() (and presumably CLOCK_REALTIME) may go backwards:
 * https://groups.google.com/forum/#!topic/comp.os.linux.development.apps/3CkHHyQX918
 */
typedef struct timespec time_of_day_t;
#  define CLOCK_GETTIME(ts) clock_gettime(profile_clock, ts)
#  define TICKS_PER_SEC 10000000                /* 10 million - 100ns */
#  define get_time_of_day(into) CLOCK_GETTIME(&into)
#  define get_ticks_between(typ, s, e, ticks, overflow) STMT_START { \
    overflow = 0; \
    ticks = ((e.tv_sec - s.tv_sec) * TICKS_PER_SEC + (e.tv_nsec / (typ)100) - (s.tv_nsec / (typ)100)); \
} STMT_END

#else                                             /* !HAS_CLOCK_GETTIME */

#ifdef HAS_MACH_TIME

#include <mach/mach.h>
#include <mach/mach_time.h>
mach_timebase_info_data_t  our_timebase;
typedef uint64_t time_of_day_t;
#  define TICKS_PER_SEC 10000000                /* 10 million - 100ns */
#  define get_time_of_day(into) into = mach_absolute_time()
#  define get_ticks_between(typ, s, e, ticks, overflow) STMT_START { \
    overflow = 0; \
    if( our_timebase.denom == 0 ) mach_timebase_info(&our_timebase); \
    ticks = (e-s) * our_timebase.numer / our_timebase.denom / (typ)100; \
} STMT_END

#else                                             /* !HAS_MACH_TIME */

#ifdef HAS_QPC

#  ifndef U64_CONST
#    ifdef _MSC_VER
#      define U64_CONST(x) x##UI64
#    else
#      define U64_CONST(x) x##ULL
#    endif
#  endif

unsigned __int64 time_frequency = U64_CONST(0);
typedef unsigned __int64 time_of_day_t;
#  define TICKS_PER_SEC time_frequency
#  define get_time_of_day(into) QueryPerformanceCounter((LARGE_INTEGER*)&into)
#  define get_ticks_between(typ, s, e, ticks, overflow) STMT_START { \
    overflow = 0; /* XXX whats this? */ \
    ticks = (typ)(e-s); \
} STMT_END

/* workaround for "error C2520: conversion from unsigned __int64 to double not
  implemented, use signed __int64" on VC 6 */
#  if defined(_MSC_VER) && _MSC_VER < 1300 /* < VC 7/2003*/
#    define NYTPIuint642NV(x) \
       ((NV)(__int64)((x) & U64_CONST(0x7FFFFFFFFFFFFFFF)) \
       + -(NV)(__int64)((x) & U64_CONST(0x8000000000000000)))
#    define get_NV_ticks_between(s, e, ticks, overflow) STMT_START { \
    overflow = 0; /* XXX whats this? */ \
    ticks = NYTPIuint642NV(e-s); \
} STMT_END

#  endif

#elif defined(HAS_GETTIMEOFDAY)
/* on Win32 gettimeofday is always implemented in Perl, not the MS C lib, so
   either we use PerlProc_gettimeofday or win32_gettimeofday, depending on the
   Perl defines about NO_XSLOCKS and PERL_IMPLICIT_SYS, to simplify logic,
   we don't check the defines, just the macro symbol to see if it forwards to
   presumably the iperlsys.h vtable call or not.
   See https://github.com/timbunce/devel-nytprof/pull/27#issuecomment-46102026
   for more details.
*/
#if defined(WIN32) && !defined(gettimeofday)
#  define gettimeofday win32_gettimeofday
#endif

typedef struct timeval time_of_day_t;
#  define TICKS_PER_SEC 1000000                 /* 1 million */
#  define get_time_of_day(into) gettimeofday(&into, NULL)
#  define get_ticks_between(typ, s, e, ticks, overflow) STMT_START { \
    overflow = 0; \
    ticks = ((e.tv_sec - s.tv_sec) * TICKS_PER_SEC + e.tv_usec - s.tv_usec); \
} STMT_END

#else /* !HAS_GETTIMEOFDAY */

/* worst-case fallback - use Time::HiRes which is expensive to call */
#define WANT_TIME_HIRES
typedef UV time_of_day_t[2];
#  define TICKS_PER_SEC 1000000                 /* 1 million */
#  define get_time_of_day(into) (*time_hires_u2time_hook)(aTHX_ into)
#  define get_ticks_between(typ, s, e, ticks, overflow)  STMT_START { \
    overflow = 0; \
    ticks = ((e[0] - s[0]) * (typ)TICKS_PER_SEC + e[1] - s[1]); \
} STMT_END

static int (*time_hires_u2time_hook)(pTHX_ UV *) = 0;

#endif /* HAS_GETTIMEOFDAY else */
#endif /* HAS_MACH_TIME else */
#endif /* HAS_CLOCK_GETTIME else */

#ifndef get_NV_ticks_between
#  define get_NV_ticks_between(s, e, ticks, overflow) get_ticks_between(NV, s, e, ticks, overflow)
#endif

#ifndef NYTPIuint642NV
#  define NYTPIuint642NV(x)  ((NV)(x))
#endif

static time_of_day_t start_time;
static time_of_day_t end_time;

static unsigned int last_executed_line;
static unsigned int last_executed_fid;
static        char *last_executed_fileptr;
static unsigned int last_block_line;
static unsigned int last_sub_line;
static unsigned int is_profiling;       /* disable_profile() & enable_profile() */
static Pid_t last_pid = 0;
static NV cumulative_overhead_ticks = 0.0;
static NV cumulative_subr_ticks = 0.0;
static UV cumulative_subr_seqn = 0;
static int main_runtime_used = 0;
static SV *DB_CHECK_cv;
static SV *DB_INIT_cv;
static SV *DB_END_cv;
static SV *DB_fin_cv;
static const char *class_mop_evaltag     = " defined at ";
static int   class_mop_evaltag_len = 12;

static unsigned int ticks_per_sec = 0;            /* 0 forces error if not set */

static AV *slowop_name_cache;

/* prototypes */
static void output_header(pTHX);
static SV *read_str(pTHX_ NYTP_file ifile, SV *sv);
static unsigned int get_file_id(pTHX_ char*, STRLEN, int created_via);
static void DB_stmt(pTHX_ COP *cop, OP *op);
static void set_option(pTHX_ const char*, const char*);
static int enable_profile(pTHX_ char *file);
static int disable_profile(pTHX);
static void finish_profile(pTHX);
static void finish_profile_nocontext(void);
static void open_output_file(pTHX_ char *);
static int reinit_if_forked(pTHX);
static int parse_DBsub_value(pTHX_ SV *sv, STRLEN *filename_len_p, UV *first_line_p, UV *last_line_p, char *sub_name);
static void write_cached_fids(void);
static void write_src_of_files(pTHX);
static void write_sub_line_ranges(pTHX);
static void write_sub_callers(pTHX);
static AV *store_profile_line_entry(pTHX_ SV *rvav, unsigned int line_num,
                                    NV time, int count, unsigned int fid);

/* copy of original contents of PL_ppaddr */
typedef OP * (CPERLscope(*orig_ppaddr_t))(pTHX);
orig_ppaddr_t *PL_ppaddr_orig;
#define run_original_op(type) CALL_FPTR(PL_ppaddr_orig[type])(aTHX)
static OP *pp_entersub_profiler(pTHX);
static OP *pp_subcall_profiler(pTHX_ int type);
static OP *pp_leave_profiler(pTHX);
static HV *sub_callers_hv;
static HV *pkg_fids_hv;     /* currently just package names */

/* PL_sawampersand is disabled in 5.17.7+ 1a904fc */
#if (PERL_VERSION < 17) || ((PERL_VERSION == 17) && (PERL_SUBVERSION < 7)) || defined(PERL_SAWAMPERSAND)
static U8 last_sawampersand;
#define CHECK_SAWAMPERSAND(fid,line) STMT_START { \
    if (PL_sawampersand != last_sawampersand) { \
        if (trace_level >= 1) \
            logwarn("Slow regex match variable seen (0x%x->0x%x at %u:%u)\n", PL_sawampersand, last_sawampersand, fid, line); \
        /* XXX this is a hack used by test14 to avoid different behaviour \
         * pre/post perl 5.17.7 since it's not relevant to the test, which is really \
         * about AutoSplit */ \
        if (!getenv("DISABLE_NYTPROF_SAWAMPERSAND")) \
            NYTP_write_sawampersand(out, fid, line); \
        last_sawampersand = (U8)PL_sawampersand; \
    } \
} STMT_END
#else
#define CHECK_SAWAMPERSAND(fid,line) (void)0
#endif

/* macros for outputing profile data */
#ifndef HAS_GETPPID
#define getppid() 0
#endif



/*
 * The loading routine
 */
load_profile_to_hv(pTHX_ NYTP_file in)
{
    Loader_state_profiler state;
    HV *profile_hv;
    HV *profile_modes;

    Zero(&state, 1, Loader_state_profiler);
    state.total_stmts_duration = 0.0;
    state.profiler_start_time = 0.0;
    state.profiler_end_time = 0.0;
    state.profiler_duration = 0.0;
#ifdef MULTIPLICITY
    state.interp = my_perl;
#endif
    state.fid_line_time_av = newAV();
    state.fid_srclines_av = newAV();
    state.fid_fileinfo_av = newAV();
    state.sub_subinfo_hv = newHV();
    state.live_pids_hv = newHV();
    state.attr_hv = newHV();
    state.option_hv = newHV();
    state.file_info_stash = gv_stashpv("Devel::NYTProf::FileInfo", GV_ADDWARN);

    av_extend(state.fid_fileinfo_av, 64);   /* grow them up front. */
    av_extend(state.fid_srclines_av, 64);
    av_extend(state.fid_line_time_av, 64);

    load_profile_data_from_stream(aTHX_ processing_callbacks,
                                  (Loader_state_base *)&state, in);


    if (HvKEYS(state.live_pids_hv)) {
        logwarn("Profile data incomplete, no terminator for %" IVdf " pids %s\n",
            (IV)HvKEYS(state.live_pids_hv),
            "(refer to TROUBLESHOOTING in the NYTProf documentation)");
        store_attrib_sv(aTHX_ state.attr_hv, STR_WITH_LEN("complete"),
                        &PL_sv_no);
    }
    else {
        store_attrib_sv(aTHX_ state.attr_hv, STR_WITH_LEN("complete"),
                        &PL_sv_yes);
    }

    sv_free((SV*)state.live_pids_hv);

    if (state.statement_discount) /* discard unused statement_discount */
        state.total_stmts_discounted -= state.statement_discount;
    store_attrib_sv(aTHX_ state.attr_hv, STR_WITH_LEN("total_stmts_measured"),
                    newSVnv(state.total_stmts_measured));
    store_attrib_sv(aTHX_ state.attr_hv, STR_WITH_LEN("total_stmts_discounted"),
                    newSVnv(state.total_stmts_discounted));
    store_attrib_sv(aTHX_ state.attr_hv, STR_WITH_LEN("total_stmts_duration"),
                    newSVnv(state.total_stmts_duration));
    store_attrib_sv(aTHX_ state.attr_hv, STR_WITH_LEN("total_sub_calls"),
                    newSVnv(state.total_sub_calls));

    if (1) {
        int show_summary_stats = (trace_level >= 1);

        if (state.profiler_end_time
            && state.total_stmts_duration > state.profiler_duration * 1.1
/* GetSystemTimeAsFiletime/gettimeofday_nv on Win32 have 15.625 ms resolution
   by default. 1 ms best case scenario if you use special options which Perl
   land doesn't use, and MS strongly discourages in
   "Timers, Timer Resolution, and Development of Efficient Code". So for short
   programs profiler_duration winds up being 0. If necessery, in the future
   profiler_duration could be set to 15.625 ms automatically on NYTProf start
   because of the argument that a process can not execute in 0 ms according to
   the laws of space and time, or at "the end" if profiler_duration is 0.0, set
   it to 15.625 ms*/
#ifdef HAS_QPC
            && state.profiler_duration != 0.0
#endif
            ) {
            logwarn("The sum of the statement timings is %.1" NVff "%% of the total time profiling."
                 " (Values slightly over 100%% can be due simply to cumulative timing errors,"
                 " whereas larger values can indicate a problem with the clock used.)\n",
                state.total_stmts_duration / state.profiler_duration * 100);
            show_summary_stats = 1;
        }

        if (show_summary_stats)
            logwarn("Summary: statements profiled %lu (=%lu-%lu), sum of time %" NVff "s, profile spanned %" NVff "s\n",
                (unsigned long)(state.total_stmts_measured - state.total_stmts_discounted),
                (unsigned long)state.total_stmts_measured, (unsigned long)state.total_stmts_discounted,
                state.total_stmts_duration,
                state.profiler_end_time - state.profiler_start_time);
    }

    profile_hv = newHV();
    profile_modes = newHV();
    (void)hv_stores(profile_hv, "attribute",
                    newRV_noinc((SV*)state.attr_hv));
    (void)hv_stores(profile_hv, "option",
                    newRV_noinc((SV*)state.option_hv));
    (void)hv_stores(profile_hv, "fid_fileinfo",
                    newRV_noinc((SV*)state.fid_fileinfo_av));
    (void)hv_stores(profile_hv, "fid_srclines",
            newRV_noinc((SV*)state.fid_srclines_av));
    (void)hv_stores(profile_hv, "fid_line_time",
                    newRV_noinc((SV*)state.fid_line_time_av));
    (void)hv_stores(profile_modes, "fid_line_time", newSVpvs("line"));
    if (state.fid_block_time_av) {
        (void)hv_stores(profile_hv, "fid_block_time",
                        newRV_noinc((SV*)state.fid_block_time_av));
        (void)hv_stores(profile_modes, "fid_block_time", newSVpvs("block"));
    }
    if (state.fid_sub_time_av) {
        (void)hv_stores(profile_hv, "fid_sub_time",
                        newRV_noinc((SV*)state.fid_sub_time_av));
        (void)hv_stores(profile_modes, "fid_sub_time", newSVpvs("sub"));
    }
    (void)hv_stores(profile_hv, "sub_subinfo",
                    newRV_noinc((SV*)state.sub_subinfo_hv));
    (void)hv_stores(profile_hv, "profile_modes",
                    newRV_noinc((SV*)profile_modes));
    return profile_hv;
}

