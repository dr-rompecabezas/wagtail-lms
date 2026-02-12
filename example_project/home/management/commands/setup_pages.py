from django.core.management.base import BaseCommand
from home.models import HomePage
from wagtail.models import Page, Site


class Command(BaseCommand):
    help = "Create a HomePage and set it as the default site root."

    def handle(self, *args, **options):
        # Check the Wagtail root page first — its table is created by core
        # migrations, so this query safely detects an unmigrated database
        # without touching the home_homepage table (which may not exist yet).
        root = Page.objects.filter(depth=1).first()
        if root is None:
            self.stderr.write(
                self.style.ERROR("Wagtail root page not found. Run migrate first.")
            )
            return

        if HomePage.objects.exists():
            self.stdout.write(self.style.SUCCESS("HomePage already exists — skipping."))
            return

        # Delete the default "Welcome to your new Wagtail site!" page if present.
        default_page = (
            Page.objects.filter(depth=2, slug="home")
            .exclude(pk__in=HomePage.objects.values_list("pk", flat=True))
            .first()
        )
        if default_page:
            default_page.delete()
            # Refresh the root node so treebeard sees the updated child state.
            root = Page.objects.filter(depth=1).first()

        # Create the HomePage as a child of the root node.
        home = HomePage(title="Welcome to Wagtail LMS", slug="home")
        root.add_child(instance=home)
        home.save_revision().publish()

        # Point the default Site at the new HomePage.
        site = Site.objects.filter(is_default_site=True).first()
        if site:
            site.root_page = home
            site.save()
        else:
            Site.objects.create(
                hostname="localhost",
                root_page=home,
                is_default_site=True,
            )

        self.stdout.write(
            self.style.SUCCESS("HomePage created and default site updated.")
        )
