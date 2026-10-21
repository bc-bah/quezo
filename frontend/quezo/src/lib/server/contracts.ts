import "server-only";
import Ajv2020 from "ajv/dist/2020";
import addFormats from "ajv-formats";
import openapi from "../../../../../postgres/openapi.json";
import type { components } from "../api/schema";
import { failure } from "./errors";

export type Actor = components["schemas"]["Actor"];
const ajv = new Ajv2020({ strict: false, allErrors: false });
addFormats(ajv);
ajv.addSchema(openapi, "quezo");
const actorValidator = ajv.compile<Actor>({ $ref: "quezo#/components/schemas/Actor" });
export const errorValidator = ajv.compile<components["schemas"]["ErrorEnvelope"]>({
  $ref: "quezo#/components/schemas/ErrorEnvelope",
});

export function actorFrom(value: unknown): Actor {
  if (!actorValidator(value)) {
    throw failure(502, "INTERNAL_ERROR", "The identity service returned an invalid response.");
  }
  return value;
}
