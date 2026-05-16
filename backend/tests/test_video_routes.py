import importlib


def _client():
    import app as appmod
    importlib.reload(appmod)
    return appmod, appmod.app.test_client()


def test_push_then_video_first_chunk_has_frame():
    appmod, c = _client()
    r = c.post("/video/push?view=front", data=b"HELLOJPEG",
               content_type="application/octet-stream")
    assert r.status_code == 200

    chunk = appmod.frame_iter(appmod.vstate, "front", max_frames=1)
    out = b"".join(chunk)
    assert b"--frame" in out
    assert b"HELLOJPEG" in out
    assert b"image/jpeg" in out


def test_push_invalid_view_400():
    appmod, c = _client()
    r = c.post("/video/push?view=side", data=b"X",
               content_type="application/octet-stream")
    assert r.status_code == 400


def test_video_invalid_view_400():
    appmod, c = _client()
    r = c.get("/video?view=nope")
    assert r.status_code == 400


def test_video_no_frame_yields_placeholder():
    appmod, c = _client()
    out = b"".join(appmod.frame_iter(appmod.vstate, "top", max_frames=1))
    assert b"--frame" in out
    assert b"image/jpeg" in out


def test_video_route_streams_multipart_header():
    appmod, c = _client()
    c.post("/video/push?view=front", data=b"J",
           content_type="application/octet-stream")
    r = c.get("/video?view=front")
    assert r.status_code == 200
    assert "multipart/x-mixed-replace" in r.content_type
