import { defineEventHandler, readBody } from 'h3';
import { setRefreshTokenCookie } from '~/utils/cookie-utils';
import { generateAccessToken, generateRefreshToken } from '~/utils/jwt-utils';
import { MOCK_USERS } from '~/utils/mock-data';
import { useResponseSuccess } from '~/utils/response';

export default defineEventHandler(async (event) => {
  // Keep the login route and UI, but always mint a superuser session without
  // verifying credentials.
  await readBody(event);
  const superUser = MOCK_USERS[0];

  const accessToken = generateAccessToken(superUser);
  const refreshToken = generateRefreshToken(superUser);

  setRefreshTokenCookie(event, refreshToken);

  return useResponseSuccess({
    ...superUser,
    accessToken,
  });
});
