from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping


class TachibanaCodecError(RuntimeError):
    """Raised when Tachibana v4r9 compression or uncompression fails."""


class TachibanaCodec(Protocol):
    def encode_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    def decode_response(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...


TACHIBANA_V4R9_COLUMNS: dict[str, int] = {
    "CLMAuthLoginAck": 2,
    "CLMAuthLoginRequest": 3,
    "CLMAuthLogoutAck": 4,
    "CLMAuthLogoutRequest": 5,
    "CLMGenbutuKabuList": 12,
    "CLMOrderList": 44,
    "CLMOrderListDetail": 45,
    "CLMShinyouTategyokuList": 46,
    "CLMZanKaiKanougaku": 57,
    "CLMZanKaiSummary": 60,
    "aCLMMfdsMarketPrice": 70,
    "aGenbutuKabuList": 88,
    "aOrderList": 94,
    "aShinyouTategyokuList": 95,
    "p_err": 286,
    "p_errno": 287,
    "p_no": 288,
    "p_rv_date": 289,
    "p_sd_date": 290,
    "sAuthId": 317,
    "sBaibaiKubun": 323,
    "sCLMID": 333,
    "sCondition": 336,
    "sEigyouDay": 369,
    "sGenbutuKabuKaituke": 382,
    "sGenkinShinyouKubun": 397,
    "sGyakusasiOrderType": 402,
    "sGyakusasiPrice": 403,
    "sGyakusasiZyouken": 406,
    "sHusokukinHasseiFlg": 451,
    "sIPOKounyu": 455,
    "sKinsyouhouMidokuFlg": 519,
    "sIssueCode": 473,
    "sIssueName": 477,
    "sKinri": 518,
    "sLastLoginDate": 549,
    "sMiniKaidateYoryoku": 560,
    "sNisaKaitukeKanougaku": 578,
    "sNseityouTousiKanougaku": 582,
    "sResultCode": 688,
    "sResultText": 689,
    "sSecondPassword": 698,
    "sSecondPasswordOmit": 699,
    "sSizyouC": 731,
    "sOrderAcceptTime": 617,
    "sOrderBaibaiKubun": 618,
    "sOrderCurrentSuryou": 622,
    "sOrderDate": 623,
    "sOrderExpireDay": 624,
    "sOrderIssueCode": 638,
    "sOrderNumber": 643,
    "sOrderOrderDateTime": 644,
    "sOrderOrderExpireDay": 645,
    "sOrderOrderNumber": 646,
    "sOrderOrderPrice": 647,
    "sOrderOrderPriceKubun": 648,
    "sOrderOrderSuryou": 649,
    "sOrderPrice": 650,
    "sOrderPriceKubun": 651,
    "sOrderSikkouDay": 653,
    "sOrderStatus": 656,
    "sOrderStatusCode": 657,
    "sOrderSuryou": 658,
    "sOrderSyouhizei": 660,
    "sOrderSyoukaiStatus": 661,
    "sOrderTesuryou": 669,
    "sOrderType": 671,
    "sOrderUkewatasiKingaku": 672,
    "sOrderYakuzyouPrice": 677,
    "sOrderYakuzyouStatus": 678,
    "sOrderYakuzyouSuryo": 679,
    "sRuitouKaituke": 690,
    "sSeityouTousiKanougaku": 712,
    "sSinyouGenbiki": 719,
    "sSinyouSinkidate": 722,
    "sSinyouSinkidateKanougaku": 723,
    "sSummaryGenkabuKaituke": 743,
    "sSummaryNisaKaitukeKanougaku": 744,
    "sSummaryNseityouTousiKanougaku": 745,
    "sSummaryUpdate": 747,
    "sSyukkin": 754,
    "sSyukkinKanougaku": 766,
    "sTargetColumn": 789,
    "sTargetIssueCode": 790,
    "sTatebiType": 793,
    "sTatebiZyuni": 794,
    "sTategyokuNumber": 796,
    "sTategyokuZyoutoekiKazeiC": 798,
    "sUpdateTime": 852,
    "sTousinKaituke": 827,
    "sUrlEvent": 869,
    "sUrlEventWebSocket": 870,
    "sUrlMaster": 871,
    "sUrlPrice": 872,
    "sUrlRequest": 873,
    "sUpdateInformAPISpecFunction": 849,
    "sUpdateInformWebDocument": 850,
    "sWarningCode": 876,
    "sWarningText": 877,
    "sZyoutoekiKazeiC": 929,
    "aCLMKabuHensaiData": 64,
    "pDHP": 105,
    "pDLP": 109,
    "pDOP": 111,
    "pDPP": 114,
    "pDV": 116,
    "pPRP": 180,
    "tDPP:T": 938,
}
TACHIBANA_V4R9_IDS: dict[str, str] = {str(value): key for key, value in TACHIBANA_V4R9_COLUMNS.items()}

# Official v4r9 CLMAuthLoginAck fields used before a read-only session exists.
# Kept separate from request mappings so login virtual URLs are not confused with
# request payload keys or unrelated account flags.
TACHIBANA_V4R9_LOGIN_ACK_COLUMNS: dict[str, int] = {
    "sCLMID": 333,
    "sKinsyouhouMidokuFlg": 519,
    "sLastLoginDate": 549,
    "sResultCode": 688,
    "sResultText": 689,
    "sSecondPasswordOmit": 699,
    "sUpdateInformAPISpecFunction": 849,
    "sUpdateInformWebDocument": 850,
    "sUrlEvent": 869,
    "sUrlEventWebSocket": 870,
    "sUrlMaster": 871,
    "sUrlPrice": 872,
    "sUrlRequest": 873,
}


@dataclass(frozen=True)
class TachibanaV4R9Codec:
    columns: dict[str, int] | None = None

    @property
    def _columns(self) -> dict[str, int]:
        return self.columns or TACHIBANA_V4R9_COLUMNS

    @property
    def _ids(self) -> dict[str, str]:
        return {str(value): key for key, value in self._columns.items()}

    def encode_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._convert_keys(payload, mapping={key: str(value) for key, value in self._columns.items()}, stringify_scalars=True)
        except Exception as exc:
            raise TachibanaCodecError("Tachibana request compression failed.") from exc

    def decode_response(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._convert_keys(payload, mapping=self._ids, stringify_scalars=False)
        except Exception as exc:
            raise TachibanaCodecError("Tachibana response uncompression failed.") from exc

    def _convert_keys(self, payload: dict[str, Any], *, mapping: dict[str, str], stringify_scalars: bool) -> dict[str, Any]:
        converted: dict[str, Any] = {}
        for key, value in payload.items():
            converted_key = mapping.get(str(key), str(key))
            converted[converted_key] = self._convert_value(value, mapping=mapping, stringify_scalars=stringify_scalars)
        return converted

    def _convert_value(self, value: Any, *, mapping: dict[str, str], stringify_scalars: bool) -> Any:
        if isinstance(value, dict):
            return self._convert_keys(value, mapping=mapping, stringify_scalars=stringify_scalars)
        if isinstance(value, list):
            return [self._convert_value(item, mapping=mapping, stringify_scalars=stringify_scalars) for item in value]
        if stringify_scalars and value is not None:
            return str(value)
        return value


def safe_codec_dict(payload: dict[str, Any]) -> dict[str, Any]:
    return sanitize_mapping(payload)
