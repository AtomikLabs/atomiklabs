import os

from services.fetch_daily_summaries.src.fetch_daily_summaries import get_config


class TestGetConfig:
    def setup_method(self):
        os.environ["RESOURCE_ARN"] = "test_value"
        os.environ["BASE_URL"] = "test_value"
        os.environ["BUCKET_NAME"] = "test_value"
        os.environ["SECRET_ARN"] = "test_value"
        os.environ["DATABASE_NAME"] = "test_value"
        os.environ["SUMMARY_SET"] = "test_value"
        os.environ["ARXIV_SUMMARY_LAMBDA"] = "test_value"

    def teardown_method(self):
        del os.environ["RESOURCE_ARN"]
        del os.environ["BASE_URL"]
        del os.environ["BUCKET_NAME"]
        del os.environ["SECRET_ARN"]
        del os.environ["DATABASE_NAME"]
        del os.environ["SUMMARY_SET"]
        del os.environ["ARXIV_SUMMARY_LAMBDA"]

    def test_get_config_returns_expected_keys(self):
        config = get_config()
        assert isinstance(config, dict)
        assert "aurora_cluster_arn" in config.keys()
        assert "base_url" in config.keys()
        assert "bucket_name" in config.keys()
        assert "db_credentials_secret_arn" in config.keys()
        assert "database" in config.keys()
        assert "summary_set" in config.keys()
        assert "arxiv_summary_lambda" in config.keys()

    def test_get_config_returns_non_empty_values(self):
        config = get_config()
        for value in config.values():
            assert value is not None and value != ""

    def test_get_config_throws_error_if_env_var_not_set(self):
        del os.environ["RESOURCE_ARN"]
        try:
            get_config()
        except Exception as e:
            assert "RESOURCE_ARN" in str(e)
        finally:
            os.environ["RESOURCE_ARN"] = "test_value"

        del os.environ["BASE_URL"]
        try:
            get_config()
        except Exception as e:
            assert "BASE_URL" in str(e)
        finally:
            os.environ["BASE_URL"] = "test_value"

        del os.environ["BUCKET_NAME"]
        try:
            get_config()
        except Exception as e:
            assert "BUCKET_NAME" in str(e)
        finally:
            os.environ["BUCKET_NAME"] = "test_value"

        del os.environ["SECRET_ARN"]
        try:
            get_config()
        except Exception as e:
            assert "SECRET_ARN" in str(e)
        finally:
            os.environ["SECRET_ARN"] = "test_value"

        del os.environ["DATABASE_NAME"]
        try:
            get_config()
        except Exception as e:
            assert "DATABASE_NAME" in str(e)
        finally:
            os.environ["DATABASE_NAME"] = "test_value"

        del os.environ["SUMMARY_SET"]
        try:
            get_config()
        except Exception as e:
            assert "SUMMARY_SET" in str(e)
        finally:
            os.environ["SUMMARY_SET"] = "test_value"

        del os.environ["ARXIV_SUMMARY_LAMBDA"]
        try:
            get_config()
        except Exception as e:
            assert "ARXIV_SUMMARY_LAMBDA" in str(e)
        finally:
            os.environ["ARXIV_SUMMARY_LAMBDA"] = "test_value"