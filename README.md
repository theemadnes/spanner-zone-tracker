# spanner-zone-tracker
A simple web service that keeps count of incoming requests based on source GCP zone.

This started as a test for using Spanner as the data backend, but the use case wasn't great so the better option (reflected in `wherewasi-data-frontend-redis`) is to just use a managed Redis instance as the backend.

The suboptimal approach I initially used was to have a frontend service (`wherewasi-data-frontend`) that would respond to requests and then publish a message to a pubsub queue, which was then processed asynchronously by `wherewasi-queue-processor` to update the Spanner table. It works, but my use case isn't great for Spanner.