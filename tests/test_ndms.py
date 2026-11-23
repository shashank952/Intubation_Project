from backend.deploy import image_analysis as ia


def view(usable=True, extent=None, teeth=None, tongue=None, aspect=None, submental=None):
    geometry = {}
    if extent is not None:
        geometry["mouth_open_extent"] = extent
    metrics = {}
    if teeth is not None:
        metrics["teeth_visibility"] = teeth
    if tongue is not None:
        metrics["tongue_visibility"] = tongue
    if aspect is not None:
        metrics["profile_aspect"] = aspect
    if submental is not None:
        metrics["submental_brightness"] = submental
    return {
        "status": "ok",
        "quality": {"usable": usable, "issues": []},
        "geometry": geometry or None,
        "view_metrics": metrics,
    }


def test_favorable_photos_score_low_and_no_contribution():
    result = ia.compute_ndms(
        {
            "frontal": view(extent=0.5),
            "teeth": view(extent=0.5, teeth=1.0),
            "tongue": view(extent=0.5, tongue=1.0),
            "jawline": view(aspect=1.35, submental=150.0),
        }
    )
    assert result["score"] is not None
    assert 0.0 <= result["score"] <= 0.2
    assert result["confidence"] == 1.0
    assert result["risk_contribution"] == 0.0
    assert result["missing_views"] == []


def test_unfavorable_photos_score_high_and_contribution_capped():
    result = ia.compute_ndms(
        {
            "frontal": view(extent=0.0),
            "teeth": view(extent=0.0, teeth=0.0),
            "tongue": view(extent=0.0, tongue=0.0),
            "jawline": view(aspect=0.3, submental=0.0),
        }
    )
    assert result["score"] is not None
    assert result["score"] >= 0.8
    assert 0.0 < result["risk_contribution"] <= ia.NDMS_MAX_CONTRIBUTION


def test_single_usable_view_yields_no_score():
    result = ia.compute_ndms(
        {"frontal": view(extent=0.4), "teeth": None, "tongue": None, "jawline": None}
    )
    assert result["score"] is None
    assert result["risk_contribution"] is None
    assert result["confidence"] == 0.25
    assert set(result["missing_views"]) == {"teeth", "tongue", "jawline"}


def test_two_components_are_enough():
    result = ia.compute_ndms(
        {
            "frontal": view(extent=0.3),
            "teeth": view(extent=0.3, teeth=0.6),
            "tongue": None,
            "jawline": None,
        }
    )
    assert result["score"] is not None
    assert result["confidence"] == 0.5
    assert len(result["components"]) >= 2


def test_score_and_contribution_are_bounded():
    for extent in (0.0, 0.25, 0.5, 1.0):
        result = ia.compute_ndms(
            {
                "frontal": view(extent=extent),
                "teeth": view(extent=extent, teeth=extent),
                "tongue": view(extent=extent, tongue=extent),
                "jawline": view(aspect=1.35, submental=extent * 150.0),
            }
        )
        if result["score"] is not None:
            assert 0.0 <= result["score"] <= 1.0
            assert 0.0 <= result["risk_contribution"] <= ia.NDMS_MAX_CONTRIBUTION


def test_unusable_views_are_ignored():
    result = ia.compute_ndms(
        {
            "frontal": view(usable=False, extent=0.5),
            "teeth": view(usable=False, teeth=1.0),
            "tongue": None,
            "jawline": None,
        }
    )
    assert result["score"] is None
    assert result["views_used"] == []


def test_blend_risk():
    assert ia.blend_risk(60.0, 4.0) == 64.0
    assert ia.blend_risk(98.0, 5.0) == 100.0
    assert ia.blend_risk(2.0, 0.0) == 2.0
    assert ia.blend_risk(None, 5.0) is None
    assert ia.blend_risk(50.0, None) is None
