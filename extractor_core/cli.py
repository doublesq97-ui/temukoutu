import argparse
import json
import sys
from .pipeline import extract


def main():
    if hasattr(sys.stdout,"reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="本地印花提取；所有自动结果均需检查")
    sub = parser.add_subparsers(dest="command",required=True)
    run = sub.add_parser("extract")
    run.add_argument("--input",required=True)
    run.add_argument("--output",required=True)
    run.add_argument("--method",choices=["auto","color","grabcut","manual"],default="auto")
    run.add_argument("--mask")
    run.add_argument("--roi",help="JSON 多边形坐标，例如 [[10,10],[200,10],[200,200],[10,200]]")
    run.add_argument("--padding",type=int,default=12)
    sizing = run.add_mutually_exclusive_group()
    sizing.add_argument("--scale",type=int,choices=[1,2,4],default=1)
    sizing.add_argument("--long-edge",type=int)
    args = parser.parse_args()
    try:
        result = extract(args.input,args.output,roi=json.loads(args.roi) if args.roi else None,
                         mask=args.mask,method=args.method,options={"padding":args.padding,"scale":args.scale,"target_long_edge":args.long_edge})
        print(json.dumps(result,ensure_ascii=False))
    except (ValueError,OSError) as exc:
        print(json.dumps({"status":"error","error":str(exc)},ensure_ascii=False))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
