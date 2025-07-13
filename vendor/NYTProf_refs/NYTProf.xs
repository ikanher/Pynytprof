Here's the profile loading from NYTProf.xs:
```
static HV*
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
```

And here's the function that outputs a header:
```
static void
output_header(pTHX)
{
    /* $0 - application name */
    SV *const sv = get_sv("0",GV_ADDWARN);
    time_t basetime = PL_basetime;
    /* This comes back with a terminating \n, and we don't want that.  */
    const char *const basetime_str = ctime(&basetime);
    const STRLEN basetime_str_len = strlen(basetime_str);
    const char version[] = STRINGIFY(PERL_REVISION) "."
        STRINGIFY(PERL_VERSION) "." STRINGIFY(PERL_SUBVERSION);
    STRLEN len;
    const char *argv0 = SvPV(sv, len);

    assert(out != NULL);
    /* File header with "magic" string, with file major and minor version */
    NYTP_write_header(out, NYTP_FILE_MAJOR_VERSION, NYTP_FILE_MINOR_VERSION);
    /* Human readable comments and attributes follow
     * comments start with '#', end with '\n', and are discarded
     * attributes start with ':', a word, '=', then the value, then '\n'
     */
    NYTP_write_comment(out, "Perl profile database. Generated by Devel::NYTProf on %.*s",
                       (int)basetime_str_len - 1, basetime_str);

    /* XXX add options, $0, etc, but beware of embedded newlines */
    /* XXX would be good to adopt a proper charset & escaping for these */
    NYTP_write_attribute_unsigned(out, STR_WITH_LEN("basetime"), (unsigned long)PL_basetime); /* $^T */
    NYTP_write_attribute_string(out, STR_WITH_LEN("application"), argv0, len);
    /* perl constants: */
    NYTP_write_attribute_string(out, STR_WITH_LEN("perl_version"), version, sizeof(version) - 1);
    NYTP_write_attribute_unsigned(out, STR_WITH_LEN("nv_size"), sizeof(NV));
    /* sanity checks: */
    NYTP_write_attribute_string(out, STR_WITH_LEN("xs_version"), STR_WITH_LEN(XS_VERSION));
    NYTP_write_attribute_unsigned(out, STR_WITH_LEN("PL_perldb"), PL_perldb);
    /* these are really options: */
    NYTP_write_attribute_signed(out, STR_WITH_LEN("clock_id"), profile_clock);
    NYTP_write_attribute_unsigned(out, STR_WITH_LEN("ticks_per_sec"), ticks_per_sec);

    if (1) {
        struct NYTP_options_t *opt_p = options;
        const struct NYTP_options_t *const opt_end
            = options + sizeof(options) / sizeof (struct NYTP_options_t);
        do {
            NYTP_write_option_iv(out, opt_p->option_name, opt_p->option_iv);
        } while (++opt_p < opt_end);
    }


#ifdef HAS_ZLIB
    if (compression_level) {
        NYTP_start_deflate_write_tag_comment(out, compression_level);
    }
#endif
    NYTP_write_process_start(out, getpid(), getppid(), gettimeofday_nv());
    write_cached_fids();                          /* empty initially, non-empty after fork */
    NYTP_flush(out);
}
```
