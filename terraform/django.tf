resource "aws_route53_zone" "this" {
  name = "geoinsight.kitware.com"
}

data "heroku_team" "this" {
  name = "kitware"
}

module "django" {
  source  = "kitware-resonant/resonant/heroku"
  version = "3.1.0"

  project_slug           = "geoinsight"
  route53_zone_id        = aws_route53_zone.this.zone_id
  heroku_team_name       = data.heroku_team.this.name
  subdomain_name         = "api"
  django_settings_module = "geoinsight.settings.heroku_production"

  additional_django_vars = {
    DJANGO_GEOINSIGHT_WEB_URL = "https://www.geoinsight.kitware.com/"
    DJANGO_DATABASE_POOL_MAX_SIZE = "12"
  }
  django_cors_allowed_origins = [
    "https://www.geoinsight.kitware.com"
  ]
  heroku_postgresql_plan = "essential-0"
}

resource "heroku_addon" "redis" {
  app_id = module.django.heroku_app_id
  plan   = "heroku-redis:mini"
}

output "dns_nameservers" {
  value = aws_route53_zone.this.name_servers
}
