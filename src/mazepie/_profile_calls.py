
def profile(fun, *args, **kwargs):
    import cProfile, pstats
    profile = cProfile.Profile()
    profile.enable()
    try:
        profile.runcall(fun, *args, **kwargs)
    finally:
        profile.disable()
        ps = pstats.Stats(profile).sort_stats("time")
        ps.print_stats()
