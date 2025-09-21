):
                with gzip.open(p, 
rt, encoding=utf-8) as fh:  # type: ignore[arg-type]
                    data = json.load(fh)
            else:
                data = json.loads(p.read_text(encoding=utf-8))
            arr = data.get(latencies) if isinstance(data, dict) else data
            if isinstance(arr, list):
                for v in arr[-(_LATENCIES.maxlen or len(arr))::]:
                    try:
                        _LATENCIES.append(float(v))
                    except Exception:
                        pass
        except Exception as exc:  # pragma: no cover
            try:
                current_app.logger.warning("persist load failed: %s", exc)
            except Exception:
                pass
            try:
                p.unlink()
            except Exception:
                pass
        break
