.PHONY: deploy stop logs clean

deploy:
	docker compose -f stack.yml pull
	docker compose -f stack.yml --env-file .env up -d

stop:
	docker compose -f stack.yml down

logs:
	docker compose -f stack.yml logs -f

clean:
	docker compose -f stack.yml down -v --remove-orphans
	docker system prune -f
