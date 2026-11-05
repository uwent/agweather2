# Run several models on your weather

Several models (`"models": ["tar-spot", "white-mold"]`, or `"all"`) on weather you send, in one request. The body is the same as for `POST /models/{model_id}/run`, and the result is shaped like `GET /models/run`. Models that can't run on the variables you sent are listed in `meta.summary.skipped`, with what each one needs. The weather you send is not stored.
