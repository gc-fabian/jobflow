from jobcopilot.models import Job
from jobcopilot.scoring import score_job


def test_score_rewards_relevant_keywords():
    config = {"must_have_keywords": ["python", "node", "postgresql"], "preferred_roles": ["software engineer"], "avoid_keywords": ["senior"]}
    job = Job(id=1, company="X", role="Software Engineer", url="u", description="Python Node PostgreSQL junior")
    scored = score_job(job, config)
    assert scored.score > 30
    assert any("seniority razonable" in r for r in scored.reasons)


def test_score_penalizes_senior():
    config = {"must_have_keywords": [], "preferred_roles": [], "avoid_keywords": ["senior"]}
    job = Job(id=1, company="X", role="Senior Engineer", url="u", description="5 años")
    scored = score_job(job, config)
    assert scored.score < 0
