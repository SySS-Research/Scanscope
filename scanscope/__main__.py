def main(argv=None):
    from scanscope.args import parse_args
    from scanscope.log import init_logging
    args = parse_args(argv=argv)
    init_logging(loglevel=args.log_level)

    disable_warnings()

    run(args)


def run(args):
    import logging
    log = logging.getLogger(__name__)
    log.info("Starting up...")

    from scanscope.writer import write_output

    data = process(args)
    write_output(data, args.output_path, format=args.format)


def process(args):
    import logging
    from scanscope.data import reduce
    from scanscope.parser import read_input

    log = logging.getLogger(__name__)
    portscan = read_input(args.input)
    if not portscan:
        log.error("No ports found")
        exit(1)
    data = reduce(portscan,
                  post_deduplicate=not args.skip_post_deduplicate,
                  pre_deduplicate=args.pre_deduplicate,
                  remove_empty=args.remove_empty_host_group,
                  )
    return data


def disable_warnings():
    from numba.core.errors import NumbaDeprecationWarning, NumbaPendingDeprecationWarning
    import warnings

    warnings.simplefilter('ignore', category=NumbaDeprecationWarning)
    warnings.simplefilter('ignore', category=NumbaPendingDeprecationWarning)


if __name__ == "__main__":
    main()
