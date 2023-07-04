def main(argv=None):
    from scanscope.args import parse_args
    from scanscope.log import init_logging
    args = parse_args(argv=argv)
    init_logging(loglevel=args.log_level)

    from scanscope.parser import parse_portscan
    from scanscope.data import reduce
    from scanscope.writer import write

    portscan = parse_portscan(args.input)
    data = reduce(portscan)
    write(args.output, data)


if __name__ == "__main__":
    main()
