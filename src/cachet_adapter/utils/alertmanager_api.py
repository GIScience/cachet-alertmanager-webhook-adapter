from cachet_adapter.utils.http_connection import HttpConnection


class AlertmanagerApi(HttpConnection):
    def get_alerts(self) -> dict:
        response = self.session.get(f'{self.base_url}/alerts')
        response.raise_for_status()
        alerts = response.json()
        return alerts
