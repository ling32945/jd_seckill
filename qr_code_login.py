#!/usr/bin/env python
# coding=utf-8

import time
import requests
import random
import json

from user_session import UserSession
from exception import SKException
from util import (
    response_status,
    parse_json,
    save_image,
    open_image,
    add_bg_for_qr,
)

import logging
logger = logging.getLogger(__name__)


class QRCodeLogin:
    """二维码扫码登录"""

    def __init__(self, user_session: UserSession):
        """初始化扫码登录
        大致流程：
            1、访问登录二维码页面，获取Token
            2、使用Token获取票据
            3、校验票据

        :param user_session:
        """

        self.qrcode_img_file = 'qr_code.png'

        self.user_session = user_session
        self.session = self.user_session.get_session()

        self.is_login = False
        self.refresh_login_status()

    def refresh_login_status(self):
        """刷新是否登录状态

        :return:
        """

        self.is_login = self._validate_cookies()

    def _validate_cookies(self):
        """验证cookies是否有效（是否登陆）
        通过访问用户订单列表页进行判断：若未登录，将会重定向到登陆页面。

        :return: cookies是否有效 True/False
        """

        url = 'https://order.jd.com/center/list.action'
        payload = {
            'rid': str(int(time.time() * 1000))
        }
        try:
            resp = self.session.get(url=url, params=payload, allow_redirects=False)
            if resp.status_code == requests.codes.OK:
                return True
        except Exception as e:
            logger.error("验证cookies是否有效发生异常", e)

        return False

    def _get_login_page(self):
        """获取PC端登录页面

        :return:
        """
        url = "https://passport.jd.com/new/login.aspx"
        page = self.session.get(url, headers=self.user_session.get_headers())
        return page

    def _get_qrcode(self):
        """缓存并展示登录二维码

        :return:
        """
        url = 'https://qr.m.jd.com/show'
        payload = {
            'appid': 133,
            'size': 300,
            't': str(int(time.time() * 1000)),
        }
        headers = {
            'User-Agent': self.user_session.get_user_agent(),
            'Referer': 'https://passport.jd.com/new/login.aspx',
        }
        resp = self.session.get(url=url, headers=headers, params=payload)

        if not response_status(resp):
            logger.info('获取二维码失败')
            return False

        save_image(resp, self.qrcode_img_file)
        logger.info('二维码获取成功，请打开京东APP扫描')

        open_image(add_bg_for_qr(self.qrcode_img_file))
        return True

    def _get_qrcode_ticket(self):
        """通过 token 获取票据

        :return:
        """
        url = 'https://qr.m.jd.com/check'
        payload = {
            'appid': '133',
            'callback': 'jQuery{}'.format(random.randint(1000000, 9999999)),
            'token': self.session.cookies.get('wlfstk_smdl'),
            '_': str(int(time.time() * 1000)),
        }
        headers = {
            'User-Agent': self.user_session.get_user_agent(),
            'Referer': 'https://passport.jd.com/new/login.aspx',
        }
        resp = self.session.get(url=url, headers=headers, params=payload)

        if not response_status(resp):
            logger.error('获取二维码扫描结果异常')
            return False

        resp_json = parse_json(resp.text)
        if resp_json['code'] != 200:
            logger.info('Code: %s, Message: %s', resp_json['code'], resp_json['msg'])
            return None
        else:
            logger.info('已完成手机客户端确认')
            return resp_json['ticket']

    def _validate_qrcode_ticket(self, ticket):
        """通过已获取的票据进行校验

        :param ticket: 已获取的票据
        :return:
        """
        url = 'https://passport.jd.com/uc/qrCodeTicketValidation'
        headers = {
            'User-Agent': self.user_session.get_user_agent(),
            'Referer': 'https://passport.jd.com/uc/login?ltype=logout',
        }

        resp = self.session.get(url=url, headers=headers, params={'t': ticket})
        if not response_status(resp):
            return False

        resp_json = json.loads(resp.text)
        if resp_json['returnCode'] == 0:
            return True
        else:
            logger.info(resp_json)
            return False

    def login_by_qrcode(self):
        """二维码登陆

        :return:
        """
        self._get_login_page()

        # download QR code
        if not self._get_qrcode():
            raise SKException('二维码下载失败')

        # get QR code ticket
        ticket = None
        retry_times = 85
        for _ in range(retry_times):
            ticket = self._get_qrcode_ticket()
            if ticket:
                break
            time.sleep(2)
        else:
            raise SKException('二维码过期，请重新获取扫描')

        # validate QR code ticket
        if not self._validate_qrcode_ticket(ticket):
            raise SKException('二维码信息校验失败')

        self.refresh_login_status()

        logger.info('二维码登录成功')
