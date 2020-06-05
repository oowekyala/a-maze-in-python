
def profile(fun, *args, **kwargs):
    import cProfile, pstats
    profile = cProfile.Profile()
    profile.enable()
    profile.runcall(fun, *args, **kwargs)
    profile.disable()
    ps = pstats.Stats(profile).sort_stats("cumulative")
    ps.print_stats()
