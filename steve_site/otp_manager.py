import pyotp


class OTPManager:
    def __init__(self, app):
        self.otp_admin = pyotp.TOTP(app.config.get('SECRET_OTP_ADMIN'))
        self.otp_operator = pyotp.TOTP(app.config.get('SECRET_OTP_OPERATOR'))
        self.otp_user = pyotp.TOTP(app.config.get('SECRET_OTP_USER'))

    def verify(self, otp):
        if not otp or not isinstance(otp, (str, int)):
            return False

        if isinstance(otp, str):
            if not otp.isdigit():
                return False
        elif isinstance(otp, int):
            otp = str(otp)
        else:
            return False

        if self.otp_admin.verify(otp, valid_window=1):
            return 'Admin'
        elif self.otp_operator.verify(otp, valid_window=1):
            return 'Operator'
        elif self.otp_user.verify(otp, valid_window=1):
            return 'User'
        else:
            return False


# TODO: register replay attack - insert error, unique constraint; multiple account register
# TODO: reset-pwd replay attack - reg_code listened




