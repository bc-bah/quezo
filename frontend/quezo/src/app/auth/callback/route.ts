import type { NextRequest } from "next/server";
import { authRoute } from "../../../lib/server/http";

export const runtime = "nodejs";
export const GET = (request: NextRequest) => authRoute("callback", request);
