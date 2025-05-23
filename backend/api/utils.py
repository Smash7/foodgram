from django.utils import timezone


def generate_shopping_list_text(ingredient_quantities, recipes):
    date_created = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
    header = f'Список покупок составлен: {date_created}'

    product_header = 'Продукты:'
    products = '\n'.join(
        [
            f'{index}. {item["ingredient__name"].capitalize()} --'
            f' {item["total_amount"]} {item["ingredient__measurement_unit"]}'
            for index, item in enumerate(ingredient_quantities, start=1)
        ]
    )

    recipe_header = 'Рецепты:'
    recipes_list = '\n'.join(
        [f'{index}. {recipe.name}' for index, recipe in enumerate(recipes,
                                                                  start=1)]
    )

    return '\n'.join([header, product_header, products,
                      recipe_header, recipes_list])
